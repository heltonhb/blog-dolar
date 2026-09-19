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
        "image_url": "https://tech-tips.ct.ws/wp-content/uploads/pin-test.png",
        "post_url": "https://tech-tips.ct.ws/?p=test",
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
