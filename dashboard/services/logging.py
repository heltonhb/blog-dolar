# -*- coding: utf-8 -*-
"""Logging configuration with JSON output."""
import json
import logging
from datetime import datetime, timezone

from flask import has_request_context, request


def _utc_now() -> datetime:
    """Timezone-aware UTC now.

    ``datetime.utcnow()`` is deprecated since 3.12 and returns a naive datetime,
    which silently mixes with aware values elsewhere. Everything here is UTC.
    """
    return datetime.now(timezone.utc)


class JSONFormatter(logging.Formatter):
    """Format logs as JSON with request context."""

    def format(self, record):
        log_entry = {
            "timestamp": _utc_now().isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Request context only exists inside a request; outside it (startup,
        # scheduler threads) `request` raises rather than being falsy.
        if has_request_context():
            log_entry.update({
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr,
                "user_agent": request.user_agent.string[:100] if request.user_agent else None,
            })

        # Add extra fields
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)

        return json.dumps(log_entry)


def setup_logging(app):
    """Configure structured logging."""
    
    # Clear existing handlers
    app.logger.handlers.clear()
    
    # Set format
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    handler.setLevel(logging.INFO)
    
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    
    # Log startup
    app.logger.info("Application starting", extra={"extra": {"startup": True}})
    
    return app


def log_request(app):
    """Create before_request and after_request hooks."""
    
    @app.before_request
    def before():
        request.start_time = _utc_now()
        app.logger.debug("Incoming request", extra={
            "extra": {
                "method": request.method,
                "path": request.path,
                "headers": dict(request.headers.items(max_value=5)),
            }
        })

    @app.after_request
    def after(response):
        if hasattr(request, 'start_time'):
            duration = (_utc_now() - request.start_time).total_seconds()
            app.logger.info(
                f"{request.method} {request.path} {response.status_code}",
                extra={"extra": {"duration_seconds": duration}}
            )
        return response
    
    return app
