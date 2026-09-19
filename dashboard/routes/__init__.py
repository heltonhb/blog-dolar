# -*- coding: utf-8 -*-
"""Blueprint registration."""


def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    from .auth import auth_bp
    from .main import main_bp
    from .api import api_bp
    from .ideas import ideas_bp
    from .stats import stats_bp
    from .articles import articles_bp
    from .images import images_bp
    from .publish import publish_bp
    from .pipeline import pipeline_bp
    from .pinterest import pinterest_bp
    from .adcash import monetization_bp
    from .traffic import traffic_bp
    from .scheduler import scheduler_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(ideas_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(articles_bp)
    app.register_blueprint(images_bp)
    app.register_blueprint(publish_bp)
    app.register_blueprint(pipeline_bp)
    app.register_blueprint(pinterest_bp)
    app.register_blueprint(monetization_bp)
    app.register_blueprint(traffic_bp)
    app.register_blueprint(scheduler_bp)
