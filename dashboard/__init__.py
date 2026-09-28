# -*- coding: utf-8 -*-
"""Application factory for Flask."""
import os
import sys
from pathlib import Path

from flask import Flask


def create_app():
    """Create and configure the Flask application."""
    # Load .env before anything else
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    app = Flask(__name__)

    # Configuration — never a deterministic fallback (session forgery risk).
    # Project root must be importable even when this file is run directly
    # (`python dashboard/__init__.py` puts dashboard/, not the root, on sys.path).
    project_root = str(Path(__file__).resolve().parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from dashboard.services.security import get_secret_key, install_csrf

    app.secret_key = get_secret_key()
    install_csrf(app)

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
