# -*- coding: utf-8 -*-
"""Tests for Misc API (Posts and Sitemap)."""
from unittest.mock import MagicMock, patch


def test_posts_get_mocked(client, monkeypatch):
    """Test retrieving published WordPress posts."""
    monkeypatch.setenv("WP_USER", "heltonhb")
    monkeypatch.setenv("WP_APP_PASSWORD", "mock_pass")

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "id": 1,
            "title": {"rendered": "Hello World Post"},
            "slug": "hello-world-post",
            "date": "2026-09-18T12:00:00",
            "link": "https://tech-tips.ct.ws/2026/09/hello-world-post/",
            "content": {"rendered": "<p>Welcome to tech tips.</p>"}
        }
    ]
    mock_client.get.return_value = mock_resp

    with patch("dashboard.routes.misc._antibot_session", return_value=mock_client):
        resp = client.get("/api/posts")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["slug"] == "hello-world-post"


def test_sitemap_xml(client):
    """Test generating XML sitemap."""
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "application/xml" in resp.content_type
    content = resp.get_data(as_text=True)
    assert "<urlset" in content
    assert "<loc>" in content
