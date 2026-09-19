# -*- coding: utf-8 -*-
"""Tests for Settings API."""
from unittest.mock import MagicMock, patch


def test_settings_get_masked(client):
    """Test retrieving settings masks sensitive secrets."""
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    # Check that any secret contains ellipsis or stars if present
    for k, v in data.items():
        if any(s in k for s in ["PASS", "SECRET", "TOKEN", "KEY"]) and v:
            assert "..." in v or v == "***"


def test_settings_save_filters_masked(client):
    """Test saving settings skips masked entries and saves valid ones."""
    payload = {
        "DASHBOARD_PASSWORD": "ncc1701_masked...",
        "CUSTOM_TEST_VAR": "new_value_123"
    }
    resp = client.post("/api/settings", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "DASHBOARD_PASSWORD" in data.get("skipped", [])


def test_settings_test_wp_mocked(client, monkeypatch):
    """Test testing WordPress credentials with mock client."""
    monkeypatch.setenv("WP_USER", "test_user")
    monkeypatch.setenv("WP_APP_PASSWORD", "test_pass")

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"name": "Test Admin"}
    mock_client.get.return_value = mock_resp

    with patch("dashboard.routes.settings._antibot_session", return_value=mock_client):
        resp = client.post("/api/settings/test_wp")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "Test Admin" in data["message"]


def test_settings_test_gemini_mocked(client, monkeypatch):
    """Test testing Gemini credentials with mock client."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyTestMockKey123")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"models": [{"name": "models/gemini-2.0-flash"}]}

    with patch("httpx.get", return_value=mock_resp):
        resp = client.get("/api/test-gemini")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["models_count"] == 1
