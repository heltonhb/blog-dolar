# -*- coding: utf-8 -*-
"""Stats API route."""
from flask import Blueprint, jsonify

from dashboard.services.helpers import _articles_dir, _env, login_required
from dashboard.services.scheduler import get_scheduler_status
from db import get_config, get_ideas

stats_bp = Blueprint("stats", __name__, url_prefix="/api")


@stats_bp.route("/stats")
@login_required
def api_stats():
    """Return summary statistics for the dashboard overview."""
    articles_dir = _articles_dir()
    article_count = len(list(articles_dir.glob("2*.md"))) if articles_dir.exists() else 0
    ideas = get_ideas()
    pending_ideas = sum(1 for i in ideas if i.get("status") == "pending")

    published_count = 0
    try:
        import pymysql
        conn = pymysql.connect(
            host=_env("WP_DB_HOST", "sql101.infinityfree.com"),
            user=_env("WP_DB_USER"),
            password=_env("WP_DB_PASS"),
            database=_env("WP_DB_NAME"),
            charset="utf8mb4",
            connect_timeout=3,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM wpq9_posts WHERE post_status='publish' AND post_type='post'")
            published_count = cur.fetchone()[0]
        conn.close()
    except Exception:
        pass

    adcash = get_config("adcash_stats", {})
    revenue = adcash.get("total_revenue", 0.0) if isinstance(adcash, dict) else 0.0

    scheduler_info = get_scheduler_status()

    return jsonify({
        "article_count": article_count,
        "published_count": published_count,
        "pending_ideas": pending_ideas,
        "revenue": revenue,
        "scheduler": scheduler_info,
    })
