# -*- coding: utf-8 -*-
"""Tests for Stats API."""


def test_stats_endpoint(client):
    """Test /api/stats returns status and expected keys."""
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "article_count" in data
    assert "published_count" in data
    assert "pending_ideas" in data
    assert "revenue" in data
    assert "scheduler" in data
    assert isinstance(data["scheduler"], dict)
