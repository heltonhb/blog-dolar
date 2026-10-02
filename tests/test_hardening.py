# -*- coding: utf-8 -*-
"""Regression tests for the Phase A hardening.

Covers the four production blockers closed in this phase:
  1. /api/run_script no longer executes arbitrary paths or argv (RCE)
  2. login_required fails CLOSED when DASHBOARD_PASSWORD is missing
  3. TLS verification is never disabled on credentialed requests
  4. ProxyFix + hardened session cookies + security headers
"""
from pathlib import Path

import pytest

from dashboard.services import helpers
from dashboard.routes import settings as settings_module

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def no_subprocess(monkeypatch):
    """Fail loudly if the runner ever tries to spawn a process."""

    def _boom(*a, **kw):
        raise AssertionError("subprocess.run must not be reached")

    monkeypatch.setattr(settings_module.subprocess, "run", _boom)


# ---------------------------------------------------------------------------
#  1. Script runner allowlist (was: remote code execution)
# ---------------------------------------------------------------------------

def test_run_script_rejects_path_traversal(client, no_subprocess):
    """``../../`` style names must be refused before touching the filesystem."""
    for evil in ["../wsgi.py", "../../etc/passwd", "sub/../analytics_ga4.py"]:
        resp = client.post("/api/run_script", json={"script_name": evil})
        assert resp.status_code in (400, 403, 404), evil


def test_run_script_rejects_absolute_path(client, no_subprocess):
    """An absolute path must not bypass the allowlist."""
    resp = client.post("/api/run_script", json={"script_name": "/etc/passwd"})
    assert resp.status_code in (400, 403, 404)


def test_run_script_rejects_non_allowlisted_script(client, no_subprocess):
    """A real file that is simply not allow-listed must be refused."""
    assert (PROJECT_ROOT / "scripts" / "publish_auto.py").exists()
    resp = client.post("/api/run_script", json={"script_name": "publish_auto.py"})
    assert resp.status_code == 403
    assert resp.get_json()["success"] is False


def test_run_script_rejects_empty_name(client, no_subprocess):
    resp = client.post("/api/run_script", json={"script_name": ""})
    assert resp.status_code == 400


def test_run_script_requires_auth(unauth_client):
    """The runner must not be reachable without a session."""
    resp = unauth_client.post("/api/run_script", json={"script_name": "analytics_ga4.py"})
    assert resp.status_code in (401, 302, 503)


def test_run_script_allowed_endpoint_lists_allowlist(client):
    resp = client.get("/api/run_script/allowed")
    assert resp.status_code == 200
    names = [a["name"] for a in resp.get_json()["allowed"]]
    assert "analytics_ga4.py" in names
    # nothing that publishes or migrates may be exposed to the runner
    assert not any(n.startswith("publish_") or n.startswith("migra_") for n in names)


def test_run_script_ignores_request_args(client, monkeypatch):
    """argv from the request body must never reach the process.

    Even for an allow-listed script, injected arguments are dropped: the runner
    executes the script with its own defaults only.
    """
    captured = {}

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs

        class _R:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return _R()

    monkeypatch.setattr(settings_module.subprocess, "run", _fake_run)
    resp = client.post(
        "/api/run_script",
        json={"script_name": "analytics_ga4.py", "args": ["--days", "; rm -rf /"]},
    )
    assert resp.status_code == 200
    assert len(captured["cmd"]) == 2, "only interpreter + script, no argv"
    assert captured["cmd"][1].endswith("analytics_ga4.py")


# ---------------------------------------------------------------------------
#  2. login_required fails closed
# ---------------------------------------------------------------------------

@pytest.fixture
def no_password(monkeypatch):
    """Simulate a deploy where DASHBOARD_PASSWORD is missing/mistyped."""
    from dashboard.routes import auth as auth_module

    # Patch both namespaces: login_required resolves it in helpers, while the
    # /login view imported the symbol directly into its own module.
    monkeypatch.setattr(helpers, "_get_dashboard_password", lambda: "")
    monkeypatch.setattr(auth_module, "_get_dashboard_password", lambda: "")


def test_api_is_closed_without_password(client, no_password):
    """An authenticated session is still refused when no password exists."""
    resp = client.get("/api/settings")
    assert resp.status_code == 503
    assert resp.get_json()["success"] is False


def test_pages_are_closed_without_password(client, no_password):
    """No more silent 'open mode' fallback."""
    resp = client.get("/")
    assert resp.status_code == 503


def test_pipeline_route_closed_without_password(client, no_password):
    """The most destructive surface is closed too."""
    resp = client.post("/api/pipeline", json={"keyword": "test"})
    assert resp.status_code == 503


def test_login_page_explains_missing_password(unauth_client, no_password):
    resp = unauth_client.get("/login")
    assert resp.status_code == 503
    assert b" configurado" in resp.data


# ---------------------------------------------------------------------------
#  3. TLS verification stays on
# ---------------------------------------------------------------------------

def test_no_verify_false_in_source():
    """Static guard: no shipped module may disable certificate verification.

    These requests carry WP Basic auth, Pinterest bearer tokens and the .env.
    """
    needle = "verify" + "=False"  # split so this scanner doesn't flag itself
    offenders = []
    for path in PROJECT_ROOT.rglob("*.py"):
        parts = path.parts
        if any(p in (".venv", "venv", "__pycache__", ".git") for p in parts):
            continue
        # Skip tests/: they assert on the very pattern being searched for.
        if "tests" in parts:
            continue
        if path.name.endswith((".bak", ".bak2")):
            continue
        if needle in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
    assert offenders == [], f"TLS verification disabled in: {offenders}"


def test_antibot_client_verifies_tls(monkeypatch):
    """The WordPress client (which sends Basic auth) must verify certificates."""
    import dashboard.services.wordpress as wp

    captured = {}

    def _fake_client(**kwargs):
        captured.update(kwargs)
        raise RuntimeError("stop after construction")

    monkeypatch.setattr("httpx.Client", _fake_client)
    with pytest.raises(RuntimeError):
        wp._antibot_session("https://techtips.dpdns.org")
    assert captured.get("verify", True) is not False


# ---------------------------------------------------------------------------
#  4. ProxyFix, cookies and security headers
# ---------------------------------------------------------------------------

def test_security_headers_present(client):
    resp = client.get("/")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "object-src 'none'" in resp.headers["Content-Security-Policy"]


def test_session_cookie_is_hardened(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["SESSION_COOKIE_SECURE"] is True


def test_proxy_fix_trusts_exactly_one_hop(app):
    """x_for must be 1: 0 would ignore the header, >1 lets clients spoof it."""
    from werkzeug.middleware.proxy_fix import ProxyFix
    assert isinstance(app.wsgi_app, ProxyFix)
    assert app.wsgi_app.x_for == 1


def test_forwarded_for_does_not_change_throttle_identity():
    """The throttle keys on ProxyFix-corrected remote_addr, not the raw header.

    Otherwise an attacker rotates X-Forwarded-For per request to defeat it.
    """
    from dashboard.services.login_throttle import client_ip

    class _Req:
        remote_addr = "203.0.113.7"
        headers = {"X-Forwarded-For": "198.51.100.1"}

    assert client_ip(_Req()) == "203.0.113.7"


# ---------------------------------------------------------------------------
#  5. No legacy monolith (Phase B)
# ---------------------------------------------------------------------------

def test_legacy_monolith_is_not_shipped():
    """dashboard/app.py duplicated every blueprint route as dead code.

    Two implementations of the same endpoints drifted apart and only one was
    deployed, which is how bugs got fixed in the copy nobody ran. Keep it gone.
    """
    assert not (PROJECT_ROOT / "dashboard" / "app.py").exists()


def test_nothing_imports_the_monolith():
    """No module may reference the removed app.py entrypoint."""
    needle_a = "from " + "app import"
    needle_b = "from dashboard" + ".app import"
    offenders = []
    for path in PROJECT_ROOT.rglob("*.py"):
        parts = path.parts
        if any(p in (".venv", "venv", "__pycache__", ".git") for p in parts):
            continue
        # Skip tests/: this scanner necessarily mentions the pattern it hunts.
        if "tests" in parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if needle_a in text or needle_b in text:
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
    assert offenders == [], f"still importing the monolith: {offenders}"


def test_app_is_built_by_the_factory(app):
    """The factory is the single entrypoint (wsgi.py, __main__.py, tests)."""
    from flask import Flask
    assert isinstance(app, Flask)
    rules = {str(r) for r in app.url_map.iter_rules()}
    assert "/login" in rules
    assert "/api/pipeline" in rules
