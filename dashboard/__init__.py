# -*- coding: utf-8 -*-
"""Application factory for Flask."""
from flask import Flask, request, session, redirect, url_for, jsonify
from functools import wraps
import hashlib
import os
from pathlib import Path


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = os.environ.get(
        "FLASK_SECRET_KEY", 
        hashlib.sha256(b"blog-dolar-secret-2026").hexdigest()
    )
    
    # Import and configure extensions
    import services.logging
    import services.rate_limit
    
    services.logging.setup_logging(app)
    services.rate_limit.setup_rate_limiting(app)
    
    return app


if __name__ == "__main__":
    import os
    app = create_app()
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
