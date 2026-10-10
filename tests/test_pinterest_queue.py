# -*- coding: utf-8 -*-
"""Unit tests for Pinterest Queue, Drip-Feed Automation, and CSV Export."""
import csv
import io
import json
from unittest.mock import MagicMock, patch

import pytest

from dashboard.services.helpers import _data_path, _save_json
from dashboard.services.pinterest_queue import (
    export_pinterest_csv,
    get_next_pending_pin,
    get_pending_pins,
    get_queue_stats,
    list_queue,
    mark_pin_status,
    publish_next_pin,
    publish_pin,
    sync_queue,
    upload_pin_image_to_wp,
)


@pytest.fixture(autouse=True)
def setup_test_queue():
    """Setup disposable pin variations and queue in sandbox."""
    variations_mock = {
        "gadget-test-1": {
            "article_title": "Top 5 Gadgets 2026",
            "bridge_url": "https://techtips.dpdns.org/p/gadget-test-1",
            "pins": [
                {
                    "slug": "gadget-test-1",
                    "variation": 1,
                    "filename": "pin-gadget-test-1.png",
                    "headline": "TOP GADGETS 2026",
                    "pin_title": "Top 5 Gadgets in 2026",
                    "description": "Best budget tech gadgets #Tech #AmazonDeals",
                    "bridge_url": "https://techtips.dpdns.org/p/gadget-test-1",
                },
                {
                    "slug": "gadget-test-1",
                    "variation": 2,
                    "filename": "pin-gadget-test-1-v2.png",
                    "headline": "MUST HAVE TECH",
                    "pin_title": "Must Have Tech Gear",
                    "description": "Essential gadgets #TechTips",
                    "bridge_url": "https://techtips.dpdns.org/p/gadget-test-1",
                },
            ],
        },
        "laptop-guide-2": {
            "article_title": "Best Student Laptops 2026",
            "bridge_url": "https://techtips.dpdns.org/p/laptop-guide-2",
            "pins": [
                {
                    "slug": "laptop-guide-2",
                    "variation": 1,
                    "filename": "pin-laptop-guide-2.png",
                    "headline": "BEST STUDENT LAPTOPS",
                    "pin_title": "Best College Laptops Under $500",
                    "description": "Affordable laptops for college #StudentLaptops",
                    "bridge_url": "https://techtips.dpdns.org/p/laptop-guide-2",
                },
                {
                    "slug": "laptop-guide-2",
                    "variation": 2,
                    "filename": "pin-laptop-guide-2-v2.png",
                    "headline": "TOP RATED LAPTOPS",
                    "pin_title": "Top Rated Student Laptops",
                    "description": "Battery and performance tested #Laptops",
                    "bridge_url": "https://techtips.dpdns.org/p/laptop-guide-2",
                },
            ],
        },
    }
    _save_json("pin_variations.json", variations_mock)
    _save_json("pinterest_queue.json", [])
    _save_json("pinterest_published.json", [])


def test_sync_queue_populates_items():
    queue = sync_queue()
    assert len(queue) == 4
    slugs = {item["slug"] for item in queue}
    assert "gadget-test-1" in slugs
    assert "laptop-guide-2" in slugs
    assert all(item["status"] == "pending" for item in queue)


def test_get_pending_pins_interleaves_variations():
    sync_queue()
    interleaved = get_pending_pins(interleaved=True)
    assert len(interleaved) == 4

    # Verify round-robin: slug 1 var 1, slug 2 var 1, slug 1 var 2, slug 2 var 2
    assert interleaved[0]["variation"] == 1
    assert interleaved[1]["variation"] == 1
    assert interleaved[2]["variation"] == 2
    assert interleaved[3]["variation"] == 2

    # Verify alternating slugs
    assert interleaved[0]["slug"] != interleaved[1]["slug"]
    assert interleaved[2]["slug"] != interleaved[3]["slug"]


def test_mark_pin_status():
    sync_queue()
    pin = get_next_pending_pin()
    assert pin is not None

    updated = mark_pin_status(pin["id"], "published", pin_id="pin_12345")
    assert updated is not None
    assert updated["status"] == "published"
    assert updated["pin_id"] == "pin_12345"
    assert updated["published_at"] is not None

    stats = get_queue_stats()
    assert stats["published"] == 1
    assert stats["pending"] == 3


def test_upload_pin_image_to_wp_when_cached():
    pin = {
        "id": "test-pin-1",
        "filename": "pin-test.png",
        "wp_media_url": "https://techtips.dpdns.org/wp-content/uploads/cached.png",
        "wp_media_id": 999,
    }
    res = upload_pin_image_to_wp(pin)
    assert res["success"] is True
    assert res["url"] == "https://techtips.dpdns.org/wp-content/uploads/cached.png"


def test_publish_pin_mocked(monkeypatch):
    monkeypatch.setenv("PINTEREST_ACCESS_TOKEN", "mock_token")
    monkeypatch.setenv("PINTEREST_BOARD_ID", "mock_board_123")

    sync_queue()
    pin = get_next_pending_pin()
    assert pin is not None

    with patch("dashboard.services.pinterest_queue.upload_pin_image_to_wp") as mock_upload, \
         patch("dashboard.services.pinterest_queue._call_create_pin") as mock_create_pin:
        mock_upload.return_value = {
            "success": True,
            "url": "https://techtips.dpdns.org/wp-content/uploads/test.png",
            "id": 101,
        }
        mock_create_pin.return_value = {"success": True, "pin_id": "pin_abc999"}

        res = publish_pin(pin["id"])
        assert res["success"] is True
        assert res["pin_id"] == "pin_abc999"

        # Check queue updated
        updated_pin = next(i for i in list_queue() if i["id"] == pin["id"])
        assert updated_pin["status"] == "published"


def test_publish_next_pin_when_empty():
    _save_json("pinterest_queue.json", [])
    res = publish_next_pin()
    assert res["success"] is False
    assert "Nenhum pin pendente" in res["message"]


def test_export_pinterest_csv():
    sync_queue()

    # 1. Test official V2 format (170 columns, all ads PAUSED)
    csv_v2 = export_pinterest_csv(board_name="Test Tech Board", format_type="v2")
    reader_v2 = list(csv.reader(io.StringIO(csv_v2)))
    assert len(reader_v2) == 7  # 3 header/instruction rows + 4 pins
    assert len(reader_v2[0]) == 170
    row_v2 = reader_v2[3]
    assert row_v2[1] == "CONSIDERATION"
    assert row_v2[3] == "Tech Tips - Test Tech Board"
    assert row_v2[4] == "PAUSED"  # Campaign PAUSED
    assert row_v2[27] == "PAUSED"  # Ad Group PAUSED
    assert row_v2[80] == "NO"  # Organic public Pin
    assert row_v2[81] == "PAUSED"  # Promoted Pin PAUSED
    assert row_v2[74].startswith("http")  # Image media URL
    assert "/bridge/" in row_v2[77] or "/p/" in row_v2[77]  # Destination URL

    # 2. Test standard 8-column format
    csv_std = export_pinterest_csv(board_name="Test Tech Board", format_type="standard")
    assert csv_std.startswith("Title,Media URL,Pinterest board")
    reader_std = list(csv.reader(io.StringIO(csv_std)))
    assert len(reader_std) == 5  # Header + 4 pins
    header = reader_std[0]
    assert header == [
        "Title",
        "Media URL",
        "Pinterest board",
        "Thumbnail",
        "Description",
        "Link",
        "Publish date",
        "Keywords",
    ]

    row1 = reader_std[1]
    assert row1[2] == "Test Tech Board"
    assert "/p/" in row1[5] or "/bridge/" in row1[5]
    assert "T" in row1[6] and row1[6].endswith("Z")


def test_api_pinterest_queue_endpoints(client):
    sync_queue()

    # GET queue
    resp = client.get("/api/pinterest/queue")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["queue"]) == 4
    assert data["stats"]["pending"] == 4

    # POST queue sync
    resp_sync = client.post("/api/pinterest/queue/sync", json={})
    assert resp_sync.status_code == 200
    assert resp_sync.get_json()["count"] == 4

    # POST queue mark
    pin = data["queue"][0]
    resp_mark = client.post("/api/pinterest/queue/mark", json={
        "id": pin["id"],
        "status": "published",
        "pin_id": "api_test_id",
    })
    assert resp_mark.status_code == 200
    assert resp_mark.get_json()["pin"]["status"] == "published"

    # GET export-csv (default V2)
    resp_csv = client.get("/api/pinterest/export-csv")
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers.get("Content-Type", "")
    assert "pinterest_bulk_editor_v2.csv" in resp_csv.headers.get("Content-Disposition", "")
    assert b"Campaign ID" in resp_csv.data

    # GET export-csv (standard 8-columns)
    resp_std = client.get("/api/pinterest/export-csv?format=standard")
    assert resp_std.status_code == 200
    assert "pinterest_schedule.csv" in resp_std.headers.get("Content-Disposition", "")
    assert b"Title,Media URL" in resp_std.data


def test_api_scheduler_add_drip(client):
    resp = client.post("/api/scheduler/add_drip", json={
        "hour": 17,
        "minute": 30,
        "board_id": "test_board_777",
    })
    # Since scheduler might be disabled in test sandbox (ENABLE_SCHEDULER not set), 503 is returned
    assert resp.status_code in (200, 503)
