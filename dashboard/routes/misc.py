# -*- coding: utf-8 -*-
"""Miscellaneous routes: WordPress posts listing and sitemap.xml."""
import re
from datetime import datetime

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
    site_url = env.get("SITE_URL") or _env("SITE_URL", "https://techtips.dpdns.org")
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
    """Generate XML sitemap for Google Search Console.

    Prefers the WordPress REST API, which returns the real canonical permalink
    for each post. The old implementation queried MySQL with a hardcoded table
    prefix (wpq9_posts) and emitted ``/?p={slug}`` — a query-string URL that is
    wrong under pretty permalinks, and it fed the raw markdown filename in
    (including the ``YYYY-MM-DD_`` date prefix). Both produced dead URLs.
    """
    site_url = _env("SITE_URL", "https://techtips.dpdns.org").rstrip("/")
    urls = _sitemap_entries_from_wp(site_url)

    if not urls:
        # Offline fallback: local articles only, with the date prefix stripped.
        urls = _sitemap_entries_from_articles(site_url)

    def _esc(value: str) -> str:
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    body = "".join(
        f"""  <url>
    <loc>{_esc(u["loc"])}</loc>
    <lastmod>{_esc(u.get("lastmod", ""))}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>\n"""
        for u in urls
    )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{_esc(site_url)}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
{body}</urlset>"""

    return Response(xml, mimetype="application/xml")


def _sitemap_entries_from_wp(site_url: str) -> list:
    """Fetch canonical URLs from the WordPress REST API. Returns [] on failure."""
    env = _load_env_dict()
    wp_user = env.get("WP_USER") or _env("WP_USER", "")
    wp_pass = env.get("WP_APP_PASSWORD") or _env("WP_APP_PASSWORD", "")

    try:
        from dashboard.services.wordpress import _antibot_session

        client = _antibot_session(site_url)
        entries = []
        for page in range(1, 6):  # up to 500 posts
            resp = client.get(
                f"{site_url}/wp-json/wp/v2/posts",
                params={"per_page": 100, "page": page, "status": "publish"},
                auth=(wp_user, wp_pass) if (wp_user and wp_pass) else None,
                timeout=15,
            )
            if resp.status_code != 200:
                break
            for post in resp.json():
                link = post.get("link")
                if not link:
                    continue
                modified = post.get("modified_gmt") or post.get("modified") or ""
                entries.append({
                    "loc": link,
                    "lastmod": modified[:10] if modified else "",
                })
            if len(resp.json()) < 100:
                break
        return entries
    except Exception:
        return []


def _sitemap_entries_from_articles(site_url: str) -> list:
    """Offline fallback built from the local articles/ directory."""
    # Defined in scripts/image_generator.py, which is already on sys.path.
    from image_generator import extract_slug_from_filename

    articles_dir = _articles_dir()
    if not articles_dir.exists():
        return []

    entries = []
    for f in sorted(articles_dir.glob("*.md"), reverse=True)[:200]:
        slug = extract_slug_from_filename(f.name)
        if not slug:
            continue
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        entries.append({
            "loc": f"{site_url}/{slug}/",
            "lastmod": mtime.strftime("%Y-%m-%d"),
        })
    return entries
