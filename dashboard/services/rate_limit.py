# -*- coding: utf-8 -*-
"""Rate limiting configuration."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def setup_rate_limiting(app):
    """Configure rate limiting for API endpoints."""
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[
            "200 per day",
            "50 per hour",
        ],
        storage_uri="memory://",
    )
    
    # API-specific limits
    app.config["RATELIMIT_HEADERS_ENABLED"] = True
    app.config["RATELIMIT_ENABLED"] = True
    
    return limiter
