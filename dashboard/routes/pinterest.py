# -*- coding: utf-8 -*-
"""Pinterest API routes."""
import urllib.parse
from datetime import datetime
from pathlib import Path

import httpx
from flask import Blueprint, jsonify, request

from dashboard.services.bridge import get_bridge_url, is_bridge_enabled
from dashboard.services.helpers import _env, _images_dir, login_required
from dashboard.services.wordpress import _wp_upload_media
from db import get_config, save_config

pinterest_bp = Blueprint("pinterest", __name__, url_prefix="/api/pinterest")


@pinterest_bp.route("/create", methods=["POST"])
@login_required
def api_pinterest_create():
    """Create a pin via Pinterest API v5. Auto-uploads local image to WordPress if needed."""
    try:
        data = request.json or {}
        access_token = _env("PINTEREST_ACCESS_TOKEN") or get_config("pinterest_config", {}).get("access_token", "")
        board_id = _env("PINTEREST_BOARD_ID") or get_config("pinterest_config", {}).get("board_id", "")
        if not access_token or not board_id:
            return jsonify({"success": False, "error": "Pinterest não configurado (ACCESS_TOKEN ou BOARD_ID ausente)."}), 400

        site_url = _env("SITE_URL", "https://tech-tips.ct.ws")
        raw_link = data.get("link", site_url)
        use_bridge = data.get("use_bridge", True) and is_bridge_enabled()
        if use_bridge and ("/p/" not in raw_link and "/bridge/" not in raw_link):
            target_link = get_bridge_url(data.get("slug", ""), raw_link)
        else:
            target_link = raw_link

        payload = {
            "board_id": board_id,
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "link": target_link,
        }

        image_url = data.get("image_url", "")

        # Convert local URLs to public (WP media or Pollinations fallback)
        if image_url and ("localhost" in image_url or image_url.startswith("/static/")):
            try:
                img_filename = image_url.split("/")[-1]
                img_path = _images_dir() / img_filename
                if img_path.exists():
                    wp_result = _wp_upload_media(img_path.read_bytes(), img_filename, alt_text=data.get("title", ""))
                    if wp_result.get("success"):
                        image_url = wp_result["url"]
                    else:
                        image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(data.get('title', 'blog post'))}?width=768&height=1024&nologo=true"
            except Exception:
                image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(data.get('title', 'blog post'))}?width=768&height=1024&nologo=true"

        if image_url:
            payload["image_source_url"] = image_url

        resp = httpx.post(
            "https://api.pinterest.com/v5/pins",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}" if not access_token.startswith("Bearer ") else access_token},
            timeout=30,
        )
        if resp.status_code in (200, 201):
            pin = resp.json()
            config = get_config("pinterest_config", {})
            published = config.get("published_pins", [])
            published.append({
                "pin_id": pin.get("id", ""),
                "title": data.get("title", ""),
                "created_at": datetime.now().isoformat(),
            })
            config["published_pins"] = published[-50:]
            save_config("pinterest_config", config)
            return jsonify({"success": True, "pin_id": pin.get("id"), "url": pin.get("link")})
        return jsonify({"success": False, "error": f"Erro Pinterest API: {resp.status_code} - {resp.text[:200]}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@pinterest_bp.route("/list")
@login_required
def api_pinterest_list():
    """Return Pinterest configuration and published pins history."""
    return jsonify(get_config("pinterest_config", {}))
