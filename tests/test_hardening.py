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

def test_tls_verification_is_on_by_default(monkeypatch):
    """TLS verification must be enabled unless explicitly opted out.

    Replaces the old static scan for ``verify=False``: the host InfinityFree
    serves an incomplete certificate chain, so a *fallback* that retries with
    verification disabled is legitimate. What matters is behaviour — the
    default path must verify, and turning it off must be a deliberate choice.

    These requests carry WP Basic auth, so a silent downgrade would expose it.
    """
    import ssl

    from dashboard.services import wordpress as wp

    # Default: no env override -> a real verifying context, never False.
    monkeypatch.delenv("WP_VERIFY_SSL", raising=False)
    ctx = wp._get_ssl_context()
    assert isinstance(ctx, ssl.SSLContext), "default must be a verifying context"
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_tls_can_be_opted_out_only_explicitly(monkeypatch):
    """WP_VERIFY_SSL=false is the single sanctioned way to disable checks."""
    from dashboard.services import wordpress as wp

    monkeypatch.setenv("WP_VERIFY_SSL", "false")
    assert wp._get_ssl_context() is False

    # Anything else keeps verification on — including a typo'd value.
    for value in ("true", "1", "yes", "garbage", ""):
        monkeypatch.setenv("WP_VERIFY_SSL", value)
        assert wp._get_ssl_context() is not False, f"expected verify ON for {value!r}"


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
    # Secure is on by default and only disabled when FORCE_HTTPS=0 (local dev
    # and CI run plain http). Never assert the raw value: the suite sets that.
    import os
    force_https = os.environ.get("FORCE_HTTPS", "1").strip().lower() not in ("0", "false", "no")
    assert app.config["SESSION_COOKIE_SECURE"] is force_https


def test_session_cookie_secure_is_the_default(app, monkeypatch):
    """Without FORCE_HTTPS=0 the cookie must require TLS.

    Guards the production default even though CI sets FORCE_HTTPS=0 to run over
    plain http.
    """
    from dashboard import create_app
    monkeypatch.delenv("FORCE_HTTPS", raising=False)
    fresh = create_app()
    assert fresh.config["SESSION_COOKIE_SECURE"] is True


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
#  6. Phase D quality (observability, no silent failures)
# ---------------------------------------------------------------------------

def test_corrupt_json_is_not_silently_ignored(monkeypatch, caplog):
    """A malformed JSON file must be reported, not read as "no data".

    Returning the default quietly makes corruption indistinguishable from an
    empty state, which hides real data loss.
    """
    import logging

    from dashboard.services import helpers

    monkeypatch.setenv("BLOG_DOLAR_ROOT", str(helpers._project_root()))
    target = helpers._data_path("corrupt_probe.json")
    target.write_text("{not valid json", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="dashboard.helpers"):
        result = helpers._load_json("corrupt_probe.json", {"fallback": True})

    assert result == {"fallback": True}
    assert any("JSON inválido" in r.message for r in caplog.records), \
        "corruption must be logged, not swallowed"
    target.unlink(missing_ok=True)


def test_stats_reports_published_count_failure(client, monkeypatch):
    """A failed WordPress query must not look like "zero posts published".

    The dashboard showed a bare 0, which reads as a fact rather than a failure.
    """
    import pymysql

    def _boom(*a, **kw):
        raise pymysql.err.OperationalError("connection refused")

    # pymysql is imported inside the route, so patch the module attribute.
    monkeypatch.setattr(pymysql, "connect", _boom)

    resp = client.get("/api/stats")
    data = resp.get_json()
    assert data["published_error"], "failure must be surfaced, not hidden behind 0"


def test_logging_uses_timezone_aware_utc():
    """Timestamps must be aware UTC; utcnow() is deprecated since 3.12."""
    from dashboard.services.logging import JSONFormatter, _utc_now

    now = _utc_now()
    assert now.tzinfo is not None, "naive datetimes break comparisons"

    import logging as _logging

    record = _logging.LogRecord("t", _logging.INFO, "f", 1, "msg", None, None)
    entry = JSONFormatter().format(record)
    assert entry.startswith('{"timestamp": "') or '"timestamp":' in entry
    assert "+00:00" not in entry, "offset already normalised to Z"


def test_csrf_token_available_in_meta_tag(client):
    """The token must be in a <meta> tag, not only in a JS global.

    A global assigned from an inline script is invisible to non-JS callers and
    easier to break silently; the meta tag is the conventional source.
    """
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert 'name="csrf-token"' in body
    assert "csrfToken" in body


def test_api_fetch_helper_exists(client):
    """New code should have an explicit CSRF-aware fetch helper."""
    body = client.get("/").get_data(as_text=True)
    assert "apiFetch" in body


# ---------------------------------------------------------------------------
#  5. No legacy monolith (Phase B)
# ---------------------------------------------------------------------------

def test_app_py_defines_no_routes():
    """dashboard/app.py must stay a thin entrypoint, not a second app.

    It originally held ~2600 lines duplicating every blueprint route: two
    implementations drifted apart and only one was deployed, so fixes landed in
    the copy nobody ran. Render needs `dashboard.app:app`, so the file exists
    again — but it may only expose create_app(), never define routes itself.
    """
    import re

    source = (PROJECT_ROOT / "dashboard" / "app.py").read_text(encoding="utf-8")
    offenders = re.findall(r"^\s*@\w+\.route\(", source, re.MULTILINE)
    assert offenders == [], f"app.py must not declare routes: {offenders}"
    # Guard against a wholesale resurrection of the monolith.
    assert len(source.splitlines()) < 50, "app.py grew back beyond an entrypoint"


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
