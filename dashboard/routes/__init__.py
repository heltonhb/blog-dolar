# -*- coding: utf-8 -*-
"""Blueprint registration."""


def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    from .auth import auth_bp
    from .main import main_bp
    from .api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
