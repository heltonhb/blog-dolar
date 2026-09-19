# -*- coding: utf-8 -*-
"""Tests for Traffic and Analytics API."""
from dashboard.services.helpers import _save_json


def test_traffic_ga4_cached(client):
    """Test retrieving cached GA4 analytics."""
    _save_json("analytics_source.json", {
        "success": True,
        "fetched_at": "2026-09-18T20:00:00",
        "sources": [
            {"source": "pinterest.com / referral", "sessions": 450},
            {"source": "google / organic", "sessions": 120}
        ]
    })
    resp = client.get("/api/traffic/ga4")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["sources"]) == 2


def test_traffic_pinterest_filtered(client):
    """Test extracting Pinterest referral traffic specifically."""
    _save_json("analytics_source.json", {
        "success": True,
        "fetched_at": "2026-09-18T20:00:00",
        "sources": [
            {"source": "pinterest.com / referral", "sessions": 450},
            {"source": "google / organic", "sessions": 120}
        ]
    })
    resp = client.get("/api/traffic/pinterest")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["pinterest"]["sessions"] == 450
    assert data["total_sessions"] == 570
