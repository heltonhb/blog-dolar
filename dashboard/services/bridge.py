# -*- coding: utf-8 -*-
"""Bridge page service for safe Pinterest traffic routing."""
import math
import re
import urllib.parse
from pathlib import Path
from flask import has_request_context, request

from dashboard.services.articles import _extract_article_info
from dashboard.services.helpers import _articles_dir, _dashboard_dir, _env, _images_dir
from db import get_config


def is_bridge_enabled() -> bool:
    """Check if the Pinterest safe bridge is enabled."""
    val = _env("BRIDGE_ENABLED")
    if not val:
        cfg = get_config("settings", {})
        val = cfg.get("bridge_enabled", "true")
    return str(val).strip().lower() in ("true", "1", "yes", "on")


def get_bridge_base_url() -> str:
    """Get the base URL for the bridge pages."""
    # 1. Explicit env or db config
    base = _env("BRIDGE_BASE_URL")
    if not base:
        cfg = get_config("settings", {})
        base = cfg.get("bridge_base_url", "")

    # 2. Render external URL (provided by Render deployment)
    if not base:
        base = _env("RENDER_EXTERNAL_URL", "")

    # 3. Active request host
    if not base and has_request_context():
        try:
            base = request.host_url.rstrip("/")
        except Exception:
            base = ""

    # 4. Fallback default
    if not base:
        base = "http://localhost:5000"

    return base.rstrip("/")


def extract_slug_from_url_or_slug(val: str) -> str:
    """Extract a clean slug from a full URL, query param, or slug string."""
    if not val:
        return ""
    val = val.strip()
    # Check ?p=slug
    if "?p=" in val:
        parsed = urllib.parse.urlparse(val)
        qs = urllib.parse.parse_qs(parsed.query)
        if "p" in qs and qs["p"]:
            return qs["p"][0].strip().strip("/")
    # Check path ending
    if "://" in val:
        parsed = urllib.parse.urlparse(val)
        path = parsed.path.strip("/")
        parts = [p for p in path.split("/") if p]
        if parts:
            return parts[-1]
    # Otherwise treat as slug
    return val.strip("/")


def get_bridge_url(slug: str, post_url: str = "") -> str:
    """Return the public bridge URL for a given slug."""
    clean_slug = extract_slug_from_url_or_slug(slug or post_url)
    if not clean_slug:
        return post_url or _env("SITE_URL", "https://tech-tips.ct.ws")

    base = get_bridge_base_url()
    return f"{base}/p/{clean_slug}"


def resolve_article_for_bridge(slug: str) -> dict:
    """Resolve full article data, image, highlights, and destination for a bridge page."""
    clean_slug = extract_slug_from_url_or_slug(slug)
    site_url = _env("SITE_URL", "https://tech-tips.ct.ws").rstrip("/")
    target_post_url = f"{site_url}/{clean_slug}/"
    pinterest_verify = _env("PINTEREST_VERIFY_TOKEN", "7c1931644caa7c83f03544d37d48d8f7")

    # 1. Search for matching markdown file in articles/
    matched_file = None
    articles_dir = _articles_dir()
    if articles_dir.exists():
        # Exact match or endswith
        for f in articles_dir.glob("*.md"):
            stem = f.stem
            file_slug = stem.split("_", 1)[1] if "_" in stem else stem
            if file_slug == clean_slug or stem == clean_slug:
                matched_file = f
                break
        if not matched_file:
            # Fuzzy match (clean_slug in stem)
            for f in articles_dir.glob("*.md"):
                if clean_slug in f.stem:
                    matched_file = f
                    break

    title = ""
    meta_desc = ""
    excerpt = ""
    highlights = []
    tags = []
    reading_time = "4 min"
    image_url = ""

    if matched_file:
        info = _extract_article_info(matched_file)
        title = info.get("title", "")
        meta_desc = info.get("meta_description", "")
        excerpt = info.get("excerpt", "")
        tags = info.get("tags", [])
        body_text = info.get("body_text", "")

        # Reading time calculation
        words = info.get("body_length", 0)
        minutes = max(1, math.ceil(words / 200)) if words else 4
        reading_time = f"{minutes} min"

        # Highlights from keywords or markdown headings
        if info.get("keywords"):
            highlights = [k for k in info["keywords"] if len(k) > 3][:4]
        if not highlights and body_text:
            md_headings = re.findall(r'^#{2,3}\s+(.+)$', body_text, re.MULTILINE)
            highlights = [re.sub(r'<[^>]+>', '', h).strip() for h in md_headings if len(h.strip()) > 3][:4]

        # Look for local image
        images_dir = _images_dir()
        if images_dir.exists():
            for candidate in [
                f"pin-{clean_slug}.png",
                f"featured-{clean_slug}.png",
                f"featured-{clean_slug}.jpg",
                f"{clean_slug}.png",
            ]:
                if (images_dir / candidate).exists():
                    image_url = f"/static/images/{candidate}"
                    break

    # If no article file found or missing fields, synthesize human-friendly fallback
    if not title:
        title = clean_slug.replace("-", " ").title()
    if not meta_desc:
        meta_desc = f"Explore this comprehensive guide on {title}. Discover expert tips, best practices, and insights."
    if not excerpt:
        excerpt = meta_desc
    if not highlights:
        highlights = [
            f"Principais diretrizes e fundamentos práticos sobre {title}",
            "Técnicas modernas recomendadas por especialistas da área",
            "Otimizações essenciais de performance e usabilidade",
            "Dicas passo a passo para aplicar no seu fluxo de trabalho",
        ]
    if not tags:
        tags = ["Tecnologia", "Web Design", "Dicas", "Tutorial"]

    # Image fallback if not found
    if not image_url:
        encoded = urllib.parse.quote(f"professional, modern, {title}")
        image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=675&nologo=true"

    # Make local image absolute if base URL is available
    if image_url.startswith("/"):
        base = get_bridge_base_url()
        image_url = f"{base}{image_url}"

    try:
        redirect_sec = int(_env("BRIDGE_REDIRECT_SECONDS", "0"))
    except Exception:
        redirect_sec = 0

    return {
        "title": title,
        "slug": clean_slug,
        "meta_description": meta_desc,
        "excerpt": excerpt,
        "image_url": image_url,
        "post_url": target_post_url,
        "highlights": highlights,
        "reading_time": reading_time,
        "tags": tags,
        "site_name": "Tech Tips",
        "redirect_seconds": redirect_sec,
        "pinterest_verify": pinterest_verify,
    }
