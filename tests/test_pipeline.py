# -*- coding: utf-8 -*-
"""Tests for Pipeline API."""
from unittest.mock import patch


def test_pipeline_checkpoints_get(client):
    """Test retrieving pipeline checkpoints."""
    resp = client.get("/api/pipeline/checkpoints")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)


def test_pipeline_history_get(client):
    """Test retrieving pipeline history."""
    resp = client.get("/api/pipeline/history")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_pipeline_missing_keyword(client):
    """Test triggering pipeline without keyword returns 400."""
    resp = client.post("/api/pipeline", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["success"] is False


def test_pipeline_run_mocked(client):
    """Test triggering pipeline with mocked core logic."""
    mock_pipeline_res = {
        "success": True,
        "article": "2026-09-18_test.md",
        "title": "Test Title",
        "image": "pin-test.png",
        "image_url": "https://techtips.dpdns.org/wp-content/uploads/pin-test.png",
        "post_url": "https://techtips.dpdns.org/?p=test",
        "steps": [
            {"step": "article", "status": "ok"},
            {"step": "image", "status": "ok"},
            {"step": "publish", "status": "ok"},
            {"step": "pinterest", "status": "ok"},
        ]
    }
    with patch("dashboard.routes.pipeline._run_pipeline_logic", return_value=mock_pipeline_res):
        resp = client.post("/api/pipeline", json={"keyword": "best wifi 7 routers"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["steps"]) == 4


def test_pipeline_autopilot_endpoint(client):
    """Test /api/pipeline/autopilot endpoint with mocked autopilot cycle."""
    mock_res = {
        "success": True,
        "autopilot": True,
        "title": "Top 5 Ergonomic Chairs",
        "keyword": "best ergonomic office chairs under 500",
        "post_url": "https://techtips.dpdns.org/post-chair",
        "steps": [{"step": "article", "status": "ok"}],
    }
    with patch("dashboard.routes.pipeline.run_autopilot_cycle", return_value=mock_res):
        resp = client.post("/api/pipeline/autopilot", json={"category": "buyer_intent"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["autopilot"] is True
        assert data["title"] == "Top 5 Ergonomic Chairs"


def test_run_autopilot_cycle_logic():
    """Test run_autopilot_cycle function end-to-end with mocks."""
    from dashboard.services.pipeline import run_autopilot_cycle

    mock_ideas = [
        {
            "id": 101,
            "idea_id": 101,
            "title": "Best Budget Gadgets",
            "keyword": "best budget gadgets 2026",
            "category": "buyer_intent",
            "status": "pending",
        }
    ]
    mock_pipeline_res = {
        "success": True,
        "title": "Best Budget Gadgets",
        "article": "2026-10-09_gadgets.md",
        "post_url": "https://techtips.dpdns.org/gadgets",
        "bridge_url": "https://techtips.dpdns.org/p/gadgets",
        "image_url": "https://techtips.dpdns.org/wp-content/uploads/pin.png",
        "steps": [{"step": "article", "status": "ok"}],
    }

    status_updates = []

    def mock_update_status(idea_id, status):
        status_updates.append((idea_id, status))

    with patch("db.get_ideas", return_value=mock_ideas), \
         patch("db.update_idea_status", side_effect=mock_update_status), \
         patch("dashboard.services.pipeline._run_pipeline_logic", return_value=mock_pipeline_res):
        res = run_autopilot_cycle(category_filter="buyer_intent")
        assert res["success"] is True
        assert res["autopilot"] is True
        assert res["title"] == "Best Budget Gadgets"
        assert (101, "in_progress") in status_updates
        assert (101, "published") in status_updates

