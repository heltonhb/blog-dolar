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


def test_traffic_ga4_timeseries(client):
    """Test retrieving cached GA4 time series data."""
    _save_json("analytics_timeseries.json", {
        "success": True,
        "fetched_at": "2026-10-01T16:00:00",
        "days": 30,
        "series": [
            {"date": "20260927", "sessions": 13},
            {"date": "20260928", "sessions": 2}
        ]
    })
    resp = client.get("/api/traffic/ga4/timeseries")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["series"]) == 2
    assert data["series"][0]["sessions"] == 13


def test_traffic_bing(client):
    """Test retrieving cached Bing Webmaster metrics."""
    _save_json("bing_stats.json", {
        "success": True,
        "days": 30,
        "totals": {
            "impressions": 100,
            "clicks": 5,
            "ctr": 5.0
        },
        "by_day": [],
        "top_queries": []
    })
    resp = client.get("/api/traffic/bing")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["totals"]["impressions"] == 100
