# -*- coding: utf-8 -*-
"""Public Bridge routes for safe Pinterest link cloaking & routing."""
from flask import Blueprint, jsonify, render_template, request

from dashboard.services.bridge import (
    get_bridge_base_url,
    get_bridge_url,
    is_bridge_enabled,
    resolve_article_for_bridge,
)
from dashboard.services.helpers import login_required

bridge_bp = Blueprint("bridge", __name__)


@bridge_bp.route("/p/<path:slug>")
@bridge_bp.route("/bridge/<path:slug>")
def view_bridge_page(slug: str):
    """Public bridge landing page for Pinterest pins.
    
    Serves a clean, fast, mobile-friendly landing page with full Open Graph
    and Pinterest metadata, pointing the user to the destination WordPress post.
    """
    article = resolve_article_for_bridge(slug)
    bridge_url = get_bridge_url(slug)
    return render_template("bridge.html", article=article, bridge_url=bridge_url)


@bridge_bp.route("/api/bridge/url", methods=["GET", "POST"])
@login_required
def api_bridge_url():
    """Return the generated bridge URL for a given slug or post_url."""
    if request.method == "POST":
        data = request.json or {}
        slug = data.get("slug", "") or data.get("post_url", "")
    else:
        slug = request.args.get("slug", "") or request.args.get("post_url", "")

    bridge_url = get_bridge_url(slug)
    return jsonify({
        "success": True,
        "enabled": is_bridge_enabled(),
        "bridge_url": bridge_url,
        "base_url": get_bridge_base_url(),
    })


@bridge_bp.route("/api/bridge/info/<path:slug>")
@login_required
def api_bridge_info(slug: str):
    """Return JSON metadata for a bridge page."""
    article = resolve_article_for_bridge(slug)
    bridge_url = get_bridge_url(slug)
    return jsonify({
        "success": True,
        "enabled": is_bridge_enabled(),
        "bridge_url": bridge_url,
        "article": article,
    })
