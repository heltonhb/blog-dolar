# -*- coding: utf-8 -*-
"""Tests for Pinterest API."""
from unittest.mock import MagicMock, patch


def test_pinterest_list(client):
    """Test retrieving Pinterest configuration and pins."""
    resp = client.get("/api/pinterest/list")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)


def test_pinterest_create_mocked(client, monkeypatch):
    """Test creating a pin with mocked Pinterest API response."""
    monkeypatch.setenv("PINTEREST_ACCESS_TOKEN", "mock_pina_token")
    monkeypatch.setenv("PINTEREST_BOARD_ID", "1234567890")

    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"id": "pin_987654321", "link": "https://pinterest.com/pin/987654321"}

    with patch("httpx.post", return_value=mock_resp):
        resp = client.post("/api/pinterest/create", json={
            "title": "Best Laptops 2026",
            "description": "Discover top laptops for programming and gaming in 2026.",
            "link": "https://tech-tips.ct.ws/?p=best-laptops-2026",
            "image_url": "https://tech-tips.ct.ws/wp-content/uploads/pin-test.png",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["pin_id"] == "pin_987654321"
