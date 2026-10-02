# -*- coding: utf-8 -*-
"""Security helpers: Flask secret key + CSRF protection.

Single source for both entrypoints (``dashboard/__init__.py`` and the
``dashboard/__main__.py`` dev entrypoint) so they behave identically.
"""
import hmac
import os
import secrets
from pathlib import Path

from flask import jsonify, request, session

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_CSRF_SESSION_KEY = "_csrf_token"
# Prefixes that never run through a browser session (add only if a genuine
# external caller appears - e.g. a webhook without cookies).
_CSRF_EXEMPT_PREFIXES = ()


def get_secret_key() -> str:
    """Resolve the Flask secret key.

    Order: ``FLASK_SECRET_KEY`` env var -> persisted random key file
    (``dashboard/data/flask_secret_key``, chmod 600) -> ephemeral random key.

    Never falls back to a deterministic value: a guessable secret key lets
    anyone forge signed session cookies (i.e. authenticate as the dashboard).
    """
    env_key = os.environ.get("FLASK_SECRET_KEY", "").strip()
    if env_key:
        return env_key

    key_file = Path(__file__).resolve().parent.parent / "data" / "flask_secret_key"
    try:
        if key_file.exists():
            stored = key_file.read_text(encoding="utf-8").strip()
            if stored:
                return stored
        key = secrets.token_hex(32)
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(key, encoding="utf-8")
        try:
            os.chmod(key_file, 0o600)
        except OSError:
            pass
        return key
    except OSError:
        # Read-only filesystem: ephemeral key (sessions reset on restart).
        return secrets.token_hex(32)


def get_csrf_token() -> str:
    """Return this session's CSRF token, creating it on first use."""
    token = session.get(_CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_hex(32)
        session[_CSRF_SESSION_KEY] = token
    return token


def rotate_csrf_token() -> str:
    """Issue a fresh token (called after login to prevent session fixation)."""
    token = secrets.token_hex(32)
    session[_CSRF_SESSION_KEY] = token
    return token


def _provided_token() -> str:
    return request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""


def _forbidden():
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "CSRF token ausente ou inválido"}), 403
    return "CSRF token missing or invalid", 403


def install_csrf(app) -> None:
    """Register the CSRF context processor and the enforcement hook."""

    @app.context_processor
    def _inject_csrf_token():
        return {"csrf_token": get_csrf_token()}

    @app.before_request
    def _enforce_csrf():
        if request.method not in _MUTATING_METHODS:
            return None
        if any(request.path.startswith(p) for p in _CSRF_EXEMPT_PREFIXES):
            return None

        expected = session.get(_CSRF_SESSION_KEY)
        if not expected:
            # No token was ever issued to this session, so there is no cookie
            # to ride. An authenticated session must have one (tokens are
            # injected on every render) - if not, fail closed.
            return None if not session.get("authenticated") else _forbidden()

        provided = _provided_token()
        if not provided:
            return _forbidden()
        if not hmac.compare_digest(
            provided.encode("utf-8", "replace"), expected.encode("utf-8")
        ):
            return _forbidden()
        return None
