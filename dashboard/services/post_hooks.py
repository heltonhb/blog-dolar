# -*- coding: utf-8 -*-
"""Post publication hooks: asynchronous background execution for multi-pin generation and interlinking."""
import json
import logging
import threading
from datetime import datetime
from pathlib import Path

from dashboard.services.helpers import _data_path

logger = logging.getLogger(__name__)

_STATUS_LOCK = threading.Lock()


def _status_file() -> Path:
    return _data_path("post_hooks_status.json")


def get_post_hooks_status(slug: str | None = None) -> dict:
    """Return status dictionary of post-publication hooks (all or for a specific slug)."""
    p = _status_file()
    data = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    if slug:
        return data.get(slug, {
            "slug": slug,
            "status": "not_started",
            "pins_status": "not_started",
            "interlinking_status": "not_started",
        })
    return data


def _save_hook_status(slug: str, update: dict) -> dict:
    """Update and persist status for a given slug atomically."""
    with _STATUS_LOCK:
        p = _status_file()
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                data = {}

        current = data.get(slug, {})
        current.update(update)
        data[slug] = current

        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(p)
        return current


def run_post_publish_tasks(slug: str, post_id: int | None = None) -> dict:
    """Execute post-publication tasks synchronously (Task 1: Multi-Pin, Task 2: Interlinking)."""
    logger.info("Iniciando post-hooks para slug=%s post_id=%s", slug, post_id)
    now_iso = datetime.now().isoformat()
    _save_hook_status(slug, {
        "slug": slug,
        "post_id": post_id,
        "status": "running",
        "started_at": now_iso,
        "completed_at": None,
        "pins_status": "running",
        "pins_count": 0,
        "pins_error": None,
        "interlinking_status": "pending",
        "interlinking_updated": 0,
        "interlinking_error": None,
    })

    # Task 1: Generate Pin Variations
    try:
        from generate_pin_variations import generate_pins_for_slug
        pins = generate_pins_for_slug(slug)
        try:
            from dashboard.services.pinterest_queue import sync_queue
            sync_queue()
        except Exception:
            pass
        _save_hook_status(slug, {
            "pins_status": "completed",
            "pins_count": len(pins),
            "pins_error": None,
        })
        logger.info("Pins gerados com sucesso para %s: %d variações", slug, len(pins))
    except Exception as e:
        logger.exception("Falha ao gerar pins para %s", slug)
        _save_hook_status(slug, {
            "pins_status": "error",
            "pins_error": str(e),
        })

    # Task 2: Internal Linking
    _save_hook_status(slug, {"interlinking_status": "running"})
    try:
        from internal_links import recalc_internal_links
        updated_count = recalc_internal_links(slug)
        _save_hook_status(slug, {
            "interlinking_status": "completed",
            "interlinking_updated": updated_count or 0,
            "interlinking_error": None,
        })
        logger.info("Interlinking concluído para %s (%d posts atualizados)", slug, updated_count or 0)
    except Exception as e:
        logger.exception("Falha no interlinking para %s", slug)
        _save_hook_status(slug, {
            "interlinking_status": "error",
            "interlinking_error": str(e),
        })

    # Final wrap-up status
    final_status = get_post_hooks_status(slug)
    has_error = (
        final_status.get("pins_status") == "error"
        or final_status.get("interlinking_status") == "error"
    )
    overall_status = "partial_error" if has_error else "completed"
    return _save_hook_status(slug, {
        "status": overall_status,
        "completed_at": datetime.now().isoformat(),
    })


def trigger_post_publish_tasks(
    slug: str, post_id: int | None = None, blocking: bool = False
) -> threading.Thread | None:
    """Trigger post-publication tasks in a background thread or synchronously."""
    if not slug:
        return None

    if blocking:
        run_post_publish_tasks(slug, post_id)
        return None

    thread = threading.Thread(
        target=run_post_publish_tasks,
        args=(slug, post_id),
        daemon=True,
        name=f"post-hooks-{slug}",
    )
    thread.start()
    return thread
