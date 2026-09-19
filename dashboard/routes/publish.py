# -*- coding: utf-8 -*-
"""Publishing API routes."""
from flask import Blueprint, jsonify, request

from dashboard.services.articles import _extract_article_info
from dashboard.services.helpers import _articles_dir, login_required
from dashboard.services.wordpress import _wp_publish

publish_bp = Blueprint("publish", __name__, url_prefix="/api")


@publish_bp.route("/publish", methods=["POST"])
@login_required
def api_publish():
    """Publish a local markdown article to WordPress via REST API."""
    try:
        data = request.json or {}
        filename = data.get("filename", "").strip()
        status = data.get("status", "publish")
        if not filename:
            return jsonify({"success": False, "error": "Arquivo obrigatório"}), 400

        filepath = _articles_dir() / filename
        if not filepath.exists():
            return jsonify({"success": False, "error": f"Arquivo não encontrado: {filename}"}), 404

        info = _extract_article_info(filepath)
        article_data = {
            "title": info["title"],
            "content": info["body_text"],
            "slug": info["slug"],
            "meta_description": info["meta_description"],
        }

        result = _wp_publish(article_data, status=status)
        if result.get("success"):
            return jsonify({
                "success": True,
                "post_id": result.get("id"),
                "url": result.get("link"),
            })
        return jsonify({"success": False, "error": result.get("error", "Falha ao publicar")}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
