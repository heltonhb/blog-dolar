# -*- coding: utf-8 -*-
"""API routes — health endpoint. More API routes will be added in future batches."""
import socket

from flask import Blueprint, jsonify

from dashboard.services.helpers import login_required

api_bp = Blueprint("api", __name__)


@api_bp.route("/health")
def api_health():
    """Health check endpoint (public, no auth required)."""
    checks = {}
    for host in ["tech-tips.ct.ws", "api3.adsterratools.com"]:
        try:
            socket.gethostbyname(host)
            checks[host] = "ok"
        except Exception as e:
            checks[host] = f"error: {str(e)}"
    return jsonify({"status": "ok", "dns": checks})
