# -*- coding: utf-8 -*-
"""Security tests: CSRF enforcement, login throttling, secret key."""
import hashlib

import pytest

from dashboard.services import login_throttle


IP = "127.0.0.1"


@pytest.fixture(autouse=True)
def _clean_throttle():
    """Keep the in-memory login throttle isolated per test."""
    login_throttle.reset(IP)
    yield
    login_throttle.reset(IP)


# ---------------------------------------------------------------------------
#  CSRF
# ---------------------------------------------------------------------------

def test_login_page_issues_csrf_token(unauth_client):
    resp = unauth_client.get("/login")
    assert resp.status_code == 200
    assert b'name="csrf_token"' in resp.data
    with unauth_client.session_transaction() as sess:
        assert sess.get("_csrf_token")


def test_csrf_missing_token_is_rejected(raw_client):
    resp = raw_client.post("/api/ideas/delete/999999")
    assert resp.status_code == 403
    assert resp.get_json()["success"] is False


def test_csrf_wrong_token_is_rejected(raw_client):
    resp = raw_client.post(
        "/api/ideas/delete/999999", headers={"X-CSRF-Token": "forged-token"}
    )
    assert resp.status_code == 403


def test_csrf_form_field_is_accepted(raw_client):
    from tests.conftest import TEST_CSRF_TOKEN
    resp = raw_client.post(
        "/api/ideas/delete/999999", data={"csrf_token": TEST_CSRF_TOKEN}
    )
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_csrf_valid_header_is_accepted(client):
    resp = client.post("/api/ideas/delete/999999")
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_get_requests_are_not_csrf_checked(client):
    resp = client.get("/api/ideas/list")
    assert resp.status_code == 200


def test_layout_injects_csrf_fetch_patch(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"__CSRF_TOKEN" in resp.data
    assert b"X-CSRF-Token" in resp.data


# ---------------------------------------------------------------------------
#  Login throttling
# ---------------------------------------------------------------------------

def test_login_throttle_blocks_after_five_failures(unauth_client, monkeypatch):
    from dashboard.routes import auth as auth_module
    monkeypatch.setattr(auth_module, "_get_dashboard_password", lambda: "senha-certa")

    unauth_client.get("/login")  # issues the CSRF token
    with unauth_client.session_transaction() as sess:
        token = sess["_csrf_token"]
    wrong = {"password": "errada", "csrf_token": token}

    for _ in range(login_throttle.MAX_ATTEMPTS):
        resp = unauth_client.post("/login", data=wrong)
        assert resp.status_code == 200
        assert b"Senha incorreta" in resp.data

    assert login_throttle.is_locked(IP)
    resp = unauth_client.post("/login", data={"password": "senha-certa", "csrf_token": token})
    assert resp.status_code == 429


def test_login_success_clears_throttle(unauth_client, monkeypatch):
    from dashboard.routes import auth as auth_module
    monkeypatch.setattr(auth_module, "_get_dashboard_password", lambda: "senha-certa")

    unauth_client.get("/login")
    with unauth_client.session_transaction() as sess:
        token = sess["_csrf_token"]
    for _ in range(login_throttle.MAX_ATTEMPTS - 1):
        unauth_client.post("/login", data={"password": "errada", "csrf_token": token})

    resp = unauth_client.post("/login", data={"password": "senha-certa", "csrf_token": token})
    assert resp.status_code == 302
    assert not login_throttle.is_locked(IP)

    with unauth_client.session_transaction() as sess:
        assert sess.get("authenticated") is True
        # token rotated after the privilege change (session fixation)
        assert sess.get("_csrf_token") != token


def test_throttle_expires_after_window():
    import time
    now = time.time()
    for _ in range(login_throttle.MAX_ATTEMPTS):
        login_throttle.register_failure(IP, now=now)
    assert login_throttle.is_locked(IP, now=now)
    assert not login_throttle.is_locked(IP, now=now + login_throttle.WINDOW_SECONDS)


def test_get_login_is_not_throttled(unauth_client):
    for _ in range(10):
        assert unauth_client.get("/login").status_code == 200


# ---------------------------------------------------------------------------
#  Secret key
# ---------------------------------------------------------------------------

def test_secret_key_is_not_deterministic(monkeypatch):
    from dashboard.services.security import get_secret_key

    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    key = get_secret_key()
    assert key and len(key) >= 32
    # old fallbacks (guessable => session forgery)
    assert key != hashlib.sha256(b"blog-dolar-secret-2026").hexdigest()
    assert key != hashlib.sha256(b"blog-dolar").hexdigest()
    # stable across calls within the same process
    assert get_secret_key() == key


def test_secret_key_prefers_env(monkeypatch):
    from dashboard.services.security import get_secret_key

    monkeypatch.setenv("FLASK_SECRET_KEY", "env-key-123")
    assert get_secret_key() == "env-key-123"
