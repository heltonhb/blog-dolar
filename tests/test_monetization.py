# -*- coding: utf-8 -*-
"""Tests for Monetization API (AdCash and Adsterra)."""
from unittest.mock import MagicMock, patch


def test_adcash_get(client):
    """Test retrieving cached AdCash statistics."""
    resp = client.get("/api/adcash")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)


def test_adcash_refresh_mocked(client, monkeypatch):
    """Test refreshing AdCash stats with mocked API response."""
    monkeypatch.setenv("ADCASH_API_TOKEN", "mock_adcash_token")
    monkeypatch.setenv("ADCASH_ZONE_ID", "mock_zone")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "rows": [
                {"date": "2026-09-18", "impressions": 500, "clicks": 25, "revenue": 3.75, "ecpm": 7.5}
            ]
        }
    }

    with patch("httpx.get", return_value=mock_resp):
        resp = client.post("/api/adcash/refresh")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["stats"]["total_revenue"] == 3.75
        assert data["stats"]["total_impressions"] == 500


def test_adsterra_get_mocked(client, monkeypatch):
    """Test retrieving Adsterra stats with mocked API response."""
    monkeypatch.setenv("ADSTERRA_API_TOKEN", "mock_adsterra_token")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [
            {"date": "2026-09-18", "impression": 1000, "clicks": 50, "revenue": 5.20, "cpm": 5.20}
        ]
    }

    with patch("httpx.get", return_value=mock_resp):
        resp = client.get("/api/adsterra")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["total_revenue"] == 5.20


def test_adsterra_domains_mocked(client, monkeypatch):
    """Test retrieving Adsterra registered domains."""
    monkeypatch.setenv("ADSTERRA_API_TOKEN", "mock_adsterra_token")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"id": 1, "domain": "tech-tips.ct.ws", "status": "active"}]

    with patch("httpx.get", return_value=mock_resp):
        resp = client.get("/api/adsterra/domains")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert data[0]["domain"] == "tech-tips.ct.ws"
