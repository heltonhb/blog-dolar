# -*- coding: utf-8 -*-
"""API routes - partial implementation, needs to be completed from app.py"""
from flask import Blueprint, jsonify, request
from functools import wraps

api_bp = Blueprint("api", __name__)


def login_required(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not os.environ.get("DASHBOARD_PASSWORD"):
            return f(*args, **kwargs)
        if not session.get("authenticated"):
            return jsonify({"success": False, "error": "Não autenticado"}), 401
        return f(*args, **kwargs)
    return decorated


@api_bp.route("/health")
def api_health():
    """Health check endpoint."""
    import socket
    checks = {}
    for host in ["tech-tips.byethost4.com", "api3.adsterratools.com"]:
        try:
            socket.gethostbyname(host)
            checks[host] = "ok"
        except Exception as e:
            checks[host] = f"error: {str(e)}"
    return jsonify({"status": "ok", "dns": checks})
