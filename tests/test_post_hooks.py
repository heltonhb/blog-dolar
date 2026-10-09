# -*- coding: utf-8 -*-
"""Tests for post-publication hooks (Multi-Pin and Interlinking background tasks)."""
from unittest.mock import patch

from dashboard.services.helpers import _articles_dir
from dashboard.services.post_hooks import (
    _save_hook_status,
    get_post_hooks_status,
    run_post_publish_tasks,
    trigger_post_publish_tasks,
)


def test_post_hooks_status_lifecycle():
    import uuid
    slug = f"lifecycle-test-slug-{uuid.uuid4().hex[:8]}"
    initial = get_post_hooks_status(slug)
    assert initial["status"] == "not_started"

    _save_hook_status(slug, {"status": "running", "pins_count": 0})
    updated = get_post_hooks_status(slug)
    assert updated["status"] == "running"
    assert updated["pins_count"] == 0


def test_run_post_publish_tasks_success(monkeypatch):
    slug = "success-test-slug"
    mock_pins = [{"filename": "pin-1.png"}, {"filename": "pin-2.png"}, {"filename": "pin-3.png"}]

    with patch("generate_pin_variations.generate_pins_for_slug", return_value=mock_pins) as mock_gen_pins, \
         patch("internal_links.recalc_internal_links", return_value=3) as mock_recalc:
        res = run_post_publish_tasks(slug, post_id=129)

        mock_gen_pins.assert_called_once_with(slug)
        mock_recalc.assert_called_once_with(slug)

        assert res["status"] == "completed"
        assert res["pins_status"] == "completed"
        assert res["pins_count"] == 3
        assert res["pins_error"] is None
        assert res["interlinking_status"] == "completed"
        assert res["interlinking_updated"] == 3
        assert res["interlinking_error"] is None
        assert res["completed_at"] is not None


def test_run_post_publish_tasks_partial_error(monkeypatch):
    slug = "error-test-slug"
    mock_pins = [{"filename": "pin-1.png"}]

    with patch("generate_pin_variations.generate_pins_for_slug", return_value=mock_pins), \
         patch("internal_links.recalc_internal_links", side_effect=RuntimeError("Anti-bot rate limit")):
        res = run_post_publish_tasks(slug, post_id=130)

        assert res["status"] == "partial_error"
        assert res["pins_status"] == "completed"
        assert res["pins_count"] == 1
        assert res["interlinking_status"] == "error"
        assert "Anti-bot rate limit" in res["interlinking_error"]
        assert res["completed_at"] is not None


def test_trigger_post_publish_tasks_blocking_and_async():
    slug_sync = "sync-test-slug"
    with patch("dashboard.services.post_hooks.run_post_publish_tasks") as mock_run:
        ret = trigger_post_publish_tasks(slug_sync, post_id=1, blocking=True)
        assert ret is None
        mock_run.assert_called_once_with(slug_sync, 1)

    slug_async = "async-test-slug"
    with patch("dashboard.services.post_hooks.run_post_publish_tasks"):
        thread = trigger_post_publish_tasks(slug_async, post_id=2, blocking=False)
        assert thread is not None
        thread.join(timeout=2)


def test_api_publish_hooks_status_route(client):
    slug = "endpoint-test-slug"
    _save_hook_status(slug, {"status": "completed", "pins_count": 3, "interlinking_updated": 2})

    resp = client.get(f"/api/publish/hooks-status/{slug}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["status"]["status"] == "completed"
    assert data["status"]["pins_count"] == 3

    resp_all = client.get("/api/publish/hooks-status")
    assert resp_all.status_code == 200
    data_all = resp_all.get_json()
    assert data_all["success"] is True
    assert slug in data_all["status"]


def test_publish_route_triggers_hooks(client):
    test_article = _articles_dir() / "2026-10-08_hook-publish-test.md"
    test_article.write_text(
        "---\ntitle: Hook Test\nslug: hook-publish-test\nmeta_description: Meta\n---\n\n<p>Body</p>",
        encoding="utf-8",
    )
    mock_wp_res = {"success": True, "id": 7777, "link": "https://techtips.dpdns.org/hook-publish-test/"}

    try:
        with patch("dashboard.routes.publish._wp_publish", return_value=mock_wp_res), \
             patch("dashboard.routes.publish.trigger_post_publish_tasks") as mock_trigger:
            resp = client.post("/api/publish", json={"filename": "2026-10-08_hook-publish-test.md"})
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            assert data["hooks_triggered"] is True
            assert data["slug"] == "hook-publish-test"
            mock_trigger.assert_called_once_with("hook-publish-test", post_id=7777)
    finally:
        if test_article.exists():
            test_article.unlink()
