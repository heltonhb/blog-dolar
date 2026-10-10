# -*- coding: utf-8 -*-
"""Pinterest Queue & Drip-Feed Automation Service.

Manages the publishing queue for multi-pin variations, handles WP media
upload, dispatches pins to Pinterest API v5 (with safe bridge links), and
generates official Pinterest Business bulk upload CSVs.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dashboard.services.bridge import get_bridge_url
from dashboard.services.helpers import (
    _data_path,
    _env,
    _images_dir,
    _load_json,
    _project_root,
    _save_json,
    _scripts_dir,
)
from dashboard.services.wordpress import _wp_upload_media

logger = logging.getLogger("dashboard.pinterest_queue")

_QUEUE_LOCK = threading.Lock()
_QUEUE_FILE = "pinterest_queue.json"


def get_queue_file() -> Path:
    """Return path to the pinterest queue JSON file."""
    return _data_path(_QUEUE_FILE)


def sync_queue() -> list[dict]:
    """Synchronize pin variations into the queue.

    Reads `pin_variations.json`, cross-checks already published pins,
    and updates/appends pins into `pinterest_queue.json`.
    """
    with _QUEUE_LOCK:
        variations_data = _load_json("pin_variations.json", {})
        existing_queue = _load_json(_QUEUE_FILE, [])

        # Build map of existing queue items by ID or filename
        queue_by_id = {}
        for item in existing_queue:
            q_id = item.get("id") or item.get("filename")
            if q_id:
                queue_by_id[q_id] = item

        # Known published pins from legacy/CLI sources for dedup
        published_items = _load_json("pinterest_published.json", [])
        cfg_published = _load_json("pinterest_config.json", {}).get("published_pins", [])
        all_published = []
        if isinstance(published_items, list):
            all_published.extend(published_items)
        if isinstance(cfg_published, list):
            all_published.extend(cfg_published)

        published_titles = {
            (p.get("title") or "").strip().lower() for p in all_published if isinstance(p, dict)
        }
        published_ids = {
            str(p.get("pin_id") or "") for p in all_published if isinstance(p, dict)
        }

        updated_queue = []
        seen_keys = set()

        # Iterate over all articles and variations in pin_variations.json
        for slug, article_info in variations_data.items():
            if not isinstance(article_info, dict):
                continue
            pins = article_info.get("pins", [])
            for pin_meta in pins:
                if not isinstance(pin_meta, dict):
                    continue
                var_num = pin_meta.get("variation", 1)
                filename = pin_meta.get("filename") or f"pin-{slug}.png"
                item_id = f"{slug}-v{var_num}"

                existing = queue_by_id.get(item_id) or queue_by_id.get(filename) or {}

                # Determine if already published
                status = existing.get("status")
                pin_id = existing.get("pin_id") or ""
                published_at = existing.get("published_at")

                pin_title = pin_meta.get("pin_title") or pin_meta.get("title") or ""
                if not status:
                    if pin_title.strip().lower() in published_titles:
                        status = "published"
                    else:
                        status = "pending"

                link = pin_meta.get("bridge_url") or get_bridge_url(slug)

                item = {
                    "id": item_id,
                    "slug": slug,
                    "variation": var_num,
                    "filename": filename,
                    "headline": pin_meta.get("headline", ""),
                    "title": pin_title,
                    "description": pin_meta.get("description", ""),
                    "link": link,
                    "image_url": pin_meta.get("image_url") or f"/static/images/{filename}",
                    "wp_media_url": existing.get("wp_media_url") or pin_meta.get("wp_media_url"),
                    "wp_media_id": existing.get("wp_media_id") or pin_meta.get("wp_media_id"),
                    "status": status,
                    "created_at": existing.get("created_at") or datetime.now().isoformat(),
                    "published_at": published_at,
                    "pin_id": pin_id,
                    "error": existing.get("error"),
                }
                updated_queue.append(item)
                seen_keys.add(item_id)
                seen_keys.add(filename)

        # Retain any extra custom items from existing queue
        for item in existing_queue:
            q_id = item.get("id") or item.get("filename")
            if q_id and q_id not in seen_keys:
                updated_queue.append(item)
                seen_keys.add(q_id)

        _save_json(_QUEUE_FILE, updated_queue)
        return updated_queue


def list_queue(status: str | None = None) -> list[dict]:
    """Return all items in the queue, optionally filtered by status."""
    queue = _load_json(_QUEUE_FILE, None)
    if queue is None:
        queue = sync_queue()
    if status:
        return [item for item in queue if item.get("status") == status]
    return queue


def get_pending_pins(interleaved: bool = True) -> list[dict]:
    """Return all pending pins.

    When `interleaved=True` (default), groups pins by slug and yields them
    in round-robin fashion (Slug A v1, Slug B v1, Slug C v1, then Slug A v2...).
    This prevents posting 3 pins for the same article in a row.
    """
    queue = list_queue()
    pending = [item for item in queue if item.get("status") in ("pending", "failed")]
    if not interleaved or not pending:
        return pending

    by_slug: dict[str, list[dict]] = {}
    for item in pending:
        slug = item.get("slug", "default")
        by_slug.setdefault(slug, []).append(item)

    interleaved_list: list[dict] = []
    max_len = max(len(v) for v in by_slug.values())
    for idx in range(max_len):
        for slug in list(by_slug.keys()):
            if idx < len(by_slug[slug]):
                interleaved_list.append(by_slug[slug][idx])

    return interleaved_list


def get_next_pending_pin() -> dict | None:
    """Return the next pending pin to publish, or None if queue is empty."""
    pending = get_pending_pins(interleaved=True)
    return pending[0] if pending else None


def mark_pin_status(
    pin_identifier: str,
    status: str,
    pin_id: str = "",
    error: str | None = None,
    extra: dict | None = None,
) -> dict | None:
    """Update status of a pin in the queue."""
    with _QUEUE_LOCK:
        queue = _load_json(_QUEUE_FILE, [])
        found_item = None
        for item in queue:
            if item.get("id") == pin_identifier or item.get("filename") == pin_identifier:
                item["status"] = status
                if status == "published":
                    item["published_at"] = datetime.now().isoformat()
                    item["error"] = None
                    if pin_id:
                        item["pin_id"] = pin_id
                elif status == "failed":
                    item["error"] = error
                elif status == "pending":
                    item["error"] = None

                if extra:
                    item.update(extra)
                found_item = item
                break

        if found_item:
            _save_json(_QUEUE_FILE, queue)

            # If published, mirror to legacy files for backwards compatibility
            if status == "published":
                _mirror_published_pin(found_item)

        return found_item


def _mirror_published_pin(item: dict) -> None:
    """Mirror published pin to pinterest_published.json and pinterest_config.json."""
    try:
        _scripts_dir()
        from pinterest_publish import save_published_pin

        save_published_pin({
            "pin_id": item.get("pin_id") or "",
            "article_url": item.get("link") or "",
            "title": item.get("title") or "",
            "filename": item.get("filename") or "",
            "created_at": item.get("published_at") or datetime.now().isoformat(),
        })
    except Exception as e:
        logger.warning("Falha ao espelhar pin publicado nas fontes legacy: %s", e)


def upload_pin_image_to_wp(pin: dict) -> dict:
    """Ensure the pin's image is uploaded to WordPress media library.

    Returns dict with {success, url, id, error}.
    """
    if pin.get("wp_media_url"):
        return {"success": True, "url": pin["wp_media_url"], "id": pin.get("wp_media_id")}

    filename = pin.get("filename", "")
    if not filename:
        return {"success": False, "error": "Nome de arquivo ausente"}

    img_path = _images_dir() / filename
    if not img_path.exists():
        return {"success": False, "error": f"Imagem local não encontrada: {filename}"}

    try:
        image_bytes = img_path.read_bytes()
        alt_text = pin.get("title", filename)
        wp_res = _wp_upload_media(image_bytes, filename, alt_text=alt_text)
        if wp_res.get("success"):
            pin["wp_media_url"] = wp_res["url"]
            pin["wp_media_id"] = wp_res.get("id")
            # Persist upload data in queue
            mark_pin_status(
                pin.get("id", filename),
                pin.get("status", "pending"),
                extra={"wp_media_url": wp_res["url"], "wp_media_id": wp_res.get("id")},
            )
            return {"success": True, "url": wp_res["url"], "id": wp_res.get("id")}
        return {"success": False, "error": wp_res.get("error", "Falha no upload para WP")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _call_create_pin(token: str, board_id: str, title: str, description: str, link: str, image_url: str) -> dict:
    """Invoke create_pin from pinterest_publish."""
    _scripts_dir()
    try:
        import pinterest_publish
        return pinterest_publish.create_pin(token, board_id, title, description, link, image_url)
    except ImportError:
        from scripts import pinterest_publish
        return pinterest_publish.create_pin(token, board_id, title, description, link, image_url)


def publish_pin(pin_identifier: str, board_id: str | None = None) -> dict:
    """Publish a specific pin to Pinterest via API v5.

    Uploads local image to WordPress if needed, directs traffic through
    the safe bridge, and updates the queue status.
    """
    queue = list_queue()
    pin = next(
        (i for i in queue if i.get("id") == pin_identifier or i.get("filename") == pin_identifier),
        None,
    )
    if not pin:
        return {"success": False, "error": f"Pin não encontrado: {pin_identifier}"}

    # 1. Ensure image is uploaded to WordPress
    upload_res = upload_pin_image_to_wp(pin)
    if upload_res.get("success"):
        image_url = upload_res["url"]
    else:
        logger.warning(
            "Upload de imagem para WP falhou (%s); usando fallback público",
            upload_res.get("error"),
        )
        site_url = _env("SITE_URL", "https://techtips.dpdns.org").rstrip("/")
        image_url = f"{site_url}/static/images/{pin.get('filename')}"

    # 2. Destination Safe Bridge Link
    slug = pin.get("slug", "")
    target_link = get_bridge_url(slug) if slug else pin.get("link", "")

    # 3. Pinterest API credentials
    config = _load_json("pinterest_config.json", {})
    token = _env("PINTEREST_ACCESS_TOKEN") or config.get("access_token", "")
    board = board_id or _env("PINTEREST_BOARD_ID") or config.get("board_id", "")

    if not token or not board:
        error_msg = "Pinterest não configurado (ACCESS_TOKEN ou BOARD_ID ausente)."
        mark_pin_status(pin.get("id", pin["filename"]), "failed", error=error_msg)
        return {"success": False, "error": error_msg, "pin": pin}

    # 4. Dispatch via Pinterest API v5
    try:
        title = (pin.get("title") or "Tech Guide")[:100]
        desc = (pin.get("description") or title)[:500]

        result = _call_create_pin(
            token=token,
            board_id=board,
            title=title,
            description=desc,
            link=target_link,
            image_url=image_url,
        )

        if result.get("success"):
            pin_id = result.get("pin_id", "")
            updated = mark_pin_status(
                pin.get("id", pin["filename"]),
                status="published",
                pin_id=pin_id,
                extra={"wp_media_url": image_url},
            )
            return {
                "success": True,
                "pin_id": pin_id,
                "pin": updated or pin,
                "url": f"https://www.pinterest.com/pin/{pin_id}/" if pin_id else "",
            }
        else:
            err = result.get("error", "Erro desconhecido na API do Pinterest")
            mark_pin_status(pin.get("id", pin["filename"]), status="failed", error=err)
            return {"success": False, "error": err, "pin": pin}
    except Exception as e:
        logger.exception("Exceção ao publicar pin %s", pin_identifier)
        err = str(e)
        mark_pin_status(pin.get("id", pin["filename"]), status="failed", error=err)
        return {"success": False, "error": err, "pin": pin}


def publish_next_pin(board_id: str | None = None) -> dict:
    """Publish the next pending pin in the drip-feed queue."""
    pin = get_next_pending_pin()
    if not pin:
        return {"success": False, "message": "Nenhum pin pendente na fila."}
    return publish_pin(pin.get("id", pin["filename"]), board_id=board_id)


def _load_bulk_v2_template() -> tuple[list[str], list[str], list[str]]:
    """Load official Pinterest Bulk Editor V2 template headers and instruction rows."""
    template_path = _project_root() / "config" / "bulk_editor_template_v2.csv"
    if template_path.exists():
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                r = csv.reader(f)
                h = next(r)
                l1 = next(r)
                l2 = next(r)
                if len(h) == 170:
                    return h, l1, l2
        except Exception as e:
            logger.warning("Falha ao ler bulk_editor_template_v2.csv: %s", e)

    # Fallback structure if file is missing
    h = ["Campaign ID"] + [""] * 169
    return h, [""] * 170, [""] * 170


def export_pinterest_csv(
    board_name: str | None = None,
    pins_per_day: int = 2,
    start_date: datetime | None = None,
    only_pending: bool = True,
    format_type: str = "v2",
) -> str:
    """Export pins to official Pinterest Business Bulk Upload CSV format.

    Supports:
      - "v2": Official Pinterest Ads Bulk Editor V2 format (170 columns, all campaigns/ads PAUSED, zero cost)
      - "standard": Simpler organic pins CSV format (8 columns)

    Schedules pins spaced according to drip-feed intervals (default: 2 pins/day at 11:00 and 17:00).
    """
    if only_pending:
        pins = get_pending_pins(interleaved=True)
    else:
        pins = list_queue()

    default_board = board_name or _env("PINTEREST_BOARD_NAME") or "Tech Tips & Buying Guides"
    site_url = _env("SITE_URL", "https://techtips.dpdns.org").rstrip("/")

    # Schedule times: 11:00 and 17:00 UTC (or local)
    if not start_date:
        now = datetime.now(timezone.utc)
        start_date = (now + timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0)

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # 1. Standard 8-column format
    if format_type.lower() == "standard":
        headers = [
            "Title",
            "Media URL",
            "Pinterest board",
            "Thumbnail",
            "Description",
            "Link",
            "Publish date",
            "Keywords",
        ]
        writer.writerow(headers)

        current_date = start_date
        slot = 0  # 0 -> 11:00, 1 -> 17:00

        for pin in pins:
            title = (pin.get("title") or "Tech Buying Guide")[:100]
            desc = (pin.get("description") or title)[:500]

            media_url = pin.get("wp_media_url")
            if not media_url:
                try:
                    up_res = upload_pin_image_to_wp(pin)
                    if up_res.get("success"):
                        media_url = up_res.get("url")
                except Exception:
                    pass
            if not media_url:
                media_url = f"{site_url}/wp-content/uploads/{pin.get('filename')}"

            link = get_bridge_url(pin.get("slug", ""))
            publish_date_str = current_date.strftime("%Y-%m-%dT%H:%M:%SZ")

            raw_keywords = [
                tag.strip("#, ")
                for tag in desc.split()
                if tag.startswith("#") and len(tag) > 1
            ]
            if not raw_keywords and pin.get("headline"):
                raw_keywords = [w.strip() for w in pin["headline"].split() if len(w) > 3][:5]
            keywords_str = ", ".join(raw_keywords[:10])

            writer.writerow([
                title,
                media_url,
                default_board,
                "",  # Thumbnail is empty for image pins
                desc,
                link,
                publish_date_str,
                keywords_str,
            ])

            if slot == 0 and pins_per_day >= 2:
                current_date = current_date.replace(hour=17)
                slot = 1
            else:
                current_date = (current_date + timedelta(days=1)).replace(hour=11)
                slot = 0

        return output.getvalue()

    # 2. Official Pinterest Bulk Editor V2 format (170 columns, PAUSED ads for zero cost)
    h, l1, l2 = _load_bulk_v2_template()
    writer.writerow(h)
    writer.writerow(l1)
    writer.writerow(l2)

    current_date = start_date
    slot = 0

    for pin in pins:
        title = (pin.get("title") or "Tech Buying Guide")[:100]
        desc = (pin.get("description") or title)[:500]

        media_url = pin.get("wp_media_url")
        if not media_url:
            try:
                up_res = upload_pin_image_to_wp(pin)
                if up_res.get("success"):
                    media_url = up_res.get("url")
            except Exception:
                pass
        if not media_url:
            media_url = f"{site_url}/wp-content/uploads/{pin.get('filename')}"

        link = get_bridge_url(pin.get("slug", ""))

        raw_keywords = [
            tag.strip("#, ")
            for tag in desc.split()
            if tag.startswith("#") and len(tag) > 1
        ]
        if not raw_keywords and pin.get("headline"):
            raw_keywords = [w.strip() for w in pin["headline"].split() if len(w) > 3][:5]
        keywords_str = ", ".join(raw_keywords[:10])

        row = [""] * len(h)
        row[1] = "CONSIDERATION"
        row[2] = "STANDARD_AD"
        row[3] = f"Tech Tips - {default_board}"
        row[4] = "PAUSED"
        row[19] = f"Tech Tips - {default_board} Group"
        row[20] = f"[{current_date.strftime('%Y-%m-%d')}]"
        row[21] = f"[{current_date.strftime('%H:%M')}]"
        row[24] = "10"
        row[26] = "DAILY"
        row[27] = "PAUSED"
        row[30] = "0.3"
        row[51] = "[]"
        row[52] = "ALL"
        row[56] = "ALL"
        row[57] = "ALL"
        row[60] = "ALL"
        row[61] = "ALL"
        if keywords_str:
            row[68] = keywords_str
        row[74] = media_url
        row[75] = title
        row[76] = desc
        row[77] = link
        row[80] = "NO"
        row[81] = "PAUSED"
        row[83] = "STATIC"
        row[84] = title[:128]
        row[158] = "PGR12345678911"
        row[159] = f"Tech Tips {default_board}"

        writer.writerow(row)

        if slot == 0 and pins_per_day >= 2:
            current_date = current_date.replace(hour=17)
            slot = 1
        else:
            current_date = (current_date + timedelta(days=1)).replace(hour=11)
            slot = 0

    return output.getvalue()


def get_queue_stats() -> dict:
    """Return summary statistics of the Pinterest queue."""
    queue = list_queue()
    pending = [p for p in queue if p.get("status") in ("pending", "failed")]
    published = [p for p in queue if p.get("status") == "published"]
    failed = [p for p in queue if p.get("status") == "failed"]
    next_pin = get_next_pending_pin()

    return {
        "total": len(queue),
        "pending": len(pending),
        "published": len(published),
        "failed": len(failed),
        "next_pin": {
            "id": next_pin.get("id"),
            "title": next_pin.get("title"),
            "slug": next_pin.get("slug"),
            "variation": next_pin.get("variation"),
            "filename": next_pin.get("filename"),
        }
        if next_pin
        else None,
    }
