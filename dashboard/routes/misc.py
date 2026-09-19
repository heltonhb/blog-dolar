# -*- coding: utf-8 -*-
"""Miscellaneous routes: WordPress posts listing and sitemap.xml."""
import re
from pathlib import Path

from flask import Blueprint, Response, jsonify

from dashboard.services.helpers import (
    _articles_dir,
    _env,
    _load_env_dict,
    login_required,
)
from dashboard.services.wordpress import _antibot_session

misc_bp = Blueprint("misc", __name__)


@misc_bp.route("/api/posts")
@login_required
def api_posts():
    """List published posts from WordPress via REST API."""
    env = _load_env_dict()
    site_url = env.get("SITE_URL") or _env("SITE_URL", "https://tech-tips.ct.ws")
    wp_user = env.get("WP_USER") or _env("WP_USER", "")
    wp_pass = env.get("WP_APP_PASSWORD") or _env("WP_APP_PASSWORD", "")

    if not wp_user or not wp_pass:
        return jsonify([])

    try:
        client = _antibot_session(site_url)
        resp = client.get(
            f"{site_url.rstrip('/')}/wp-json/wp/v2/posts",
            params={"per_page": 100, "status": "publish"},
            auth=(wp_user, wp_pass),
            timeout=15,
        )
        if resp.status_code == 200:
            posts = []
            for p in resp.json():
                posts.append({
                    "id": p.get("id"),
                    "title": p.get("title", {}).get("rendered", ""),
                    "slug": p.get("slug", ""),
                    "date": p.get("date", "")[:10],
                    "link": p.get("link", ""),
                    "content": re.sub(r'<[^>]+>', '', p.get("content", {}).get("rendered", "")),
                })
            return jsonify(posts)
        return jsonify([])
    except Exception:
        return jsonify([])


@misc_bp.route("/sitemap.xml")
def sitemap():
    """Generate XML sitemap for Google Search Console."""
    site_url = _env("SITE_URL", "https://tech-tips.ct.ws").rstrip('/')
    posts_xml = ""

    # Attempt to query database if accessible
    try:
        import pymysql
        env = _load_env_dict()
        conn = pymysql.connect(
            host=env.get("WP_DB_HOST", "sql101.infinityfree.com"),
            user=env.get("WP_DB_USER", ""),
            password=env.get("WP_DB_PASS", ""),
            database=env.get("WP_DB_NAME", ""),
            charset="utf8mb4",
            connect_timeout=3,
            cursorclass=pymysql.cursors.DictCursor,
        )
        with conn.cursor() as cur:
            cur.execute("""
                SELECT post_name, post_date, post_modified
                FROM wpq9_posts
                WHERE post_status = 'publish' AND post_type = 'post'
                ORDER BY post_date DESC
                LIMIT 500
            """)
            for row in cur.fetchall():
                slug = row.get("post_name", "")
                date = row["post_date"].strftime("%Y-%m-%d") if row.get("post_date") else ""
                mod = row["post_modified"].strftime("%Y-%m-%d") if row.get("post_modified") else date
                posts_xml += f"""  <url>
    <loc>{site_url}/?p={slug}</loc>
    <lastmod>{mod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>\n"""
        conn.close()
    except Exception:
        # Fallback: scan local articles directory
        articles_dir = _articles_dir()
        if articles_dir.exists():
            for f in sorted(articles_dir.glob("*.md"), reverse=True)[:200]:
                slug = f.stem
                posts_xml += f"""  <url>
    <loc>{site_url}/?p={slug}</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>\n"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{site_url}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
{posts_xml}</urlset>"""

    return Response(xml, mimetype="application/xml")
