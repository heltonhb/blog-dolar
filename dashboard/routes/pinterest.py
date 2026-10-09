# -*- coding: utf-8 -*-
"""Pinterest API routes."""
import urllib.parse
from datetime import datetime

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

        site_url = _env("SITE_URL", "https://techtips.dpdns.org")
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


@pinterest_bp.route("/queue", methods=["GET"])
@login_required
def api_pinterest_queue():
    """Return Pinterest queue items and status."""
    try:
        from dashboard.services.pinterest_queue import (
            get_pending_pins,
            get_queue_stats,
            list_queue,
        )

        status_filter = request.args.get("status")
        queue = list_queue(status=status_filter)
        pending = get_pending_pins(interleaved=True)
        stats = get_queue_stats()
        return jsonify({
            "success": True,
            "stats": stats,
            "queue": queue,
            "pending_count": len(pending),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@pinterest_bp.route("/queue/sync", methods=["POST"])
@login_required
def api_pinterest_queue_sync():
    """Resynchronize queue from pin variations."""
    try:
        from dashboard.services.pinterest_queue import get_queue_stats, sync_queue

        queue = sync_queue()
        stats = get_queue_stats()
        return jsonify({
            "success": True,
            "count": len(queue),
            "stats": stats,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@pinterest_bp.route("/publish-next", methods=["POST"])
@login_required
def api_pinterest_publish_next():
    """Publish next pending pin in the drip-feed queue."""
    try:
        from dashboard.services.pinterest_queue import publish_next_pin

        data = request.json or {}
        board_id = data.get("board_id")
        res = publish_next_pin(board_id=board_id)
        status_code = 200 if res.get("success") else (400 if "Nenhum pin" in res.get("message", "") else 500)
        return jsonify(res), status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@pinterest_bp.route("/publish-pin", methods=["POST"])
@login_required
def api_pinterest_publish_pin():
    """Publish a specific pin by identifier."""
    try:
        from dashboard.services.pinterest_queue import publish_pin

        data = request.json or {}
        pin_id = data.get("id") or data.get("pin_id") or data.get("filename")
        if not pin_id:
            return jsonify({"success": False, "error": "ID ou nome de arquivo do pin é obrigatório"}), 400
        board_id = data.get("board_id")
        res = publish_pin(pin_id, board_id=board_id)
        return jsonify(res), (200 if res.get("success") else 500)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@pinterest_bp.route("/queue/mark", methods=["POST"])
@login_required
def api_pinterest_queue_mark():
    """Update status of a pin manually."""
    try:
        from dashboard.services.pinterest_queue import mark_pin_status

        data = request.json or {}
        pin_id = data.get("id") or data.get("filename")
        status = data.get("status", "published")
        remote_pin_id = data.get("pin_id", "")
        if not pin_id:
            return jsonify({"success": False, "error": "ID do pin é obrigatório"}), 400

        item = mark_pin_status(pin_id, status=status, pin_id=remote_pin_id)
        if not item:
            return jsonify({"success": False, "error": "Pin não encontrado"}), 404
        return jsonify({"success": True, "pin": item})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@pinterest_bp.route("/export-csv", methods=["GET"])
@login_required
def api_pinterest_export_csv():
    """Export pins as CSV for Pinterest Business Bulk Upload."""
    try:
        from flask import Response
        from dashboard.services.pinterest_queue import export_pinterest_csv

        board_name = request.args.get("board_name")
        all_pins = request.args.get("all") == "1"
        csv_content = export_pinterest_csv(
            board_name=board_name,
            only_pending=not all_pins,
        )
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=pinterest_schedule.csv"},
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
