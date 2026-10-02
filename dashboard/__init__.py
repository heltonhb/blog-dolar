# -*- coding: utf-8 -*-
"""Application factory for Flask."""
import os
import sys
from datetime import timedelta
from pathlib import Path

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# The dashboard templates still carry inline <script>/style and load Font Awesome
# from cdnjs, so script/style keep 'unsafe-inline'. Everything else is locked:
# no plugins, no framing, no base-tag hijack, and images are restricted to the
# hosts actually used (own static files, Pinterest CDN, Pollinations).
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
    "font-src 'self' https://cdnjs.cloudflare.com; "
    "img-src 'self' data: https://s.pinimg.com https://image.pollinations.ai; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'"
)


def create_app():
    """Create and configure the Flask application."""
    # Load .env before anything else
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    app = Flask(__name__)

    # Behind a reverse proxy (Render/nginx), WSGI sees the proxy's socket
    # address, not the client's. Without this, remote_addr == proxy IP (the
    # per-IP rate limit degenerates into a global one) and request.host_url
    # rebuilds http:// URLs, breaking the bridge page canonical/OG tags.
    # x_for=1 => trust exactly one hop (our own proxy); never 0 (client-spoofable).
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Session cookie hardening. Secure is enabled whenever the app is served
    # over https so the login cookie never travels in cleartext.
    https_only = os.environ.get("FORCE_HTTPS", "1").strip() not in ("0", "false", "no")
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=https_only,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,  # no dashboard upload needs more
    )

    # Configuration — never a deterministic fallback (session forgery risk).
    # Project root must be importable even when this file is run directly
    # (`python dashboard/__init__.py` puts dashboard/, not the root, on sys.path).
    project_root = str(Path(__file__).resolve().parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from dashboard.services.security import get_secret_key, install_csrf

    app.secret_key = get_secret_key()
    install_csrf(app)

    # Security headers. HSTS only on https, otherwise a local http dev session
    # would get pinned to https and break.
    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Content-Security-Policy", _CSP)
        if https_only:
            resp.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return resp

    # Ensure scripts/ and dashboard/ are in sys.path for legacy imports
    dashboard_dir = str(Path(__file__).resolve().parent)
    scripts_dir = str(Path(__file__).resolve().parent.parent / "scripts")
    if dashboard_dir not in sys.path:
        sys.path.insert(0, dashboard_dir)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    # Initialize extensions
    try:
        from dashboard.services.logging import setup_logging
        setup_logging(app)
    except Exception:
        pass  # Logging is optional

    try:
        from dashboard.services.rate_limit import setup_rate_limiting
        setup_rate_limiting(app)
    except Exception:
        pass  # Rate limiting is optional (flask-limiter may not be installed)

    # Register blueprints
    from dashboard.routes import register_blueprints
    register_blueprints(app)

    # Initialize database
    try:
        from db import init_db
        init_db()
    except Exception as e:
        print(f"  ⚠️ DB init: {e}")

    # Restore scheduled pipeline jobs
    try:
        from dashboard.services.scheduler import _restore_scheduler_jobs
        _restore_scheduler_jobs()
    except Exception as e:
        print(f"  ⚠️ Scheduler restore: {e}")

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
