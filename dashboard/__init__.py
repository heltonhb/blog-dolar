# -*- coding: utf-8 -*-
"""Application factory for Flask."""
import hashlib
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

    # Configuration
    app.secret_key = os.environ.get(
        "FLASK_SECRET_KEY",
        hashlib.sha256(
            os.environ.get("DASHBOARD_PASSWORD", "blog-dolar").encode()
        ).hexdigest()
    )

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

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
