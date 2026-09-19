# -*- coding: utf-8 -*-
"""Ideas API routes."""
from datetime import datetime

import feedparser
from flask import Blueprint, jsonify, request

from dashboard.services.gemini import _gemini_call
from dashboard.services.helpers import _parse_json, login_required
from db import delete_idea, get_ideas, save_idea

ideas_bp = Blueprint("ideas", __name__, url_prefix="/api/ideas")


def _generate_ideas_from_gemini() -> list:
    """Generate 10 evergreen tech ideas via Gemini."""
    data = _gemini_call(
        "Generate 10 evergreen technology blog post ideas. "
        "Focus on topics that stay relevant for years. Include long-tail keywords.\n"
        "Return ONLY a JSON array:\n"
        '[{"title":"Article title","keyword":"long-tail keyword","cpm_estimate":"$10-20","category":"technology"}]\n'
        "No markdown, pure JSON."
    )
    result = _parse_json(data)
    return result if isinstance(result, list) else []


def _generate_ideas_from_trends() -> list:
    """Fetch Google Trends RSS and turn trending topics into article ideas via Gemini."""
    feed_url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
    feed = feedparser.parse(feed_url)

    trending = []
    for entry in getattr(feed, "entries", [])[:20]:
        title = entry.get("title", "")
        if title:
            trending.append(title)

    if not trending:
        # Fallback to pure AI if RSS fails
        return _generate_ideas_from_gemini()

    trends_str = "\n".join(f"- {t}" for t in trending[:15])
    prompt = (
        f"These are currently trending topics on Google in the USA:\n{trends_str}\n\n"
        "Select the 8 topics most relevant to technology, gadgets, software, or computers. "
        "For each, write a specific, SEO-optimized blog article title and long-tail keyword.\n"
        "Return ONLY a JSON array:\n"
        '[{"title":"Article title","keyword":"long-tail keyword","cpm_estimate":"$8-15","category":"technology","trend_source":"google_trends"}]\n'
        "No markdown, pure JSON."
    )
    data = _gemini_call(prompt)
    ideas = _parse_json(data)
    if isinstance(ideas, list):
        for idea in ideas:
            idea["source"] = "trends"
        return ideas
    return []


@ideas_bp.route("/generate", methods=["POST"])
@login_required
def api_generate_ideas():
    """Generate new article ideas using Gemini AI or Google Trends RSS."""
    try:
        data = request.json or {}
        source = data.get("source", "ai")

        if source == "trends":
            ideas = _generate_ideas_from_trends()
        else:
            ideas = _generate_ideas_from_gemini()

        if not isinstance(ideas, list):
            return jsonify({"success": False, "error": "Gemini retornou formato inválido"}), 500

        existing = get_ideas()
        max_id = max((i.get("idea_id") or i.get("id") or 0 for i in existing), default=0)
        for idx, idea in enumerate(ideas):
            idea["idea_id"] = max_id + idx + 1
            idea["status"] = "pending"
            idea["created_at"] = datetime.now().isoformat()
            idea["source"] = source
            save_idea(idea)

        return jsonify({"success": True, "ideas": ideas, "count": len(ideas)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@ideas_bp.route("/add", methods=["POST"])
@login_required
def api_add_idea():
    """Manually add a single article idea."""
    try:
        data = request.json or {}
        ideas = get_ideas()
        max_id = max((i.get("idea_id") or i.get("id") or 0 for i in ideas), default=0)
        new_idea = {
            "id": max_id + 1,
            "idea_id": max_id + 1,
            "title": data.get("title", ""),
            "keyword": data.get("keyword", ""),
            "category": data.get("category", "technology"),
            "cpm_estimate": data.get("cpm_estimate", ""),
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "source": "manual",
        }
        save_idea(new_idea)
        return jsonify({"success": True, "idea": new_idea})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@ideas_bp.route("/delete/<int:idea_id>", methods=["POST"])
@login_required
def api_delete_idea(idea_id):
    """Delete an idea by ID."""
    try:
        delete_idea(idea_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@ideas_bp.route("/list")
@login_required
def api_list_ideas():
    """List all ideas ordered by ID descending."""
    ideas = get_ideas()
    ideas.sort(key=lambda x: x.get("idea_id") or x.get("id") or 0, reverse=True)
    return jsonify(ideas)
