# -*- coding: utf-8 -*-
"""Tests for Publish API."""
from unittest.mock import patch

from dashboard.services.helpers import _articles_dir


def test_publish_missing_filename(client):
    """Test publishing with missing filename returns 400."""
    resp = client.post("/api/publish", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["success"] is False


def test_publish_nonexistent_file(client):
    """Test publishing non-existent article file returns 404."""
    resp = client.post("/api/publish", json={"filename": "does-not-exist-file.md"})
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["success"] is False


def test_publish_success_mocked(client):
    """Test publishing with mocked WordPress service."""
    test_article = _articles_dir() / "2026-09-18_mock-publish-test.md"
    test_article.write_text(
        "---\ntitle: Mock Publish Title\nslug: mock-publish-test\nmeta_description: Meta\ntags: ['wp']\n---\n\n<p>Article body</p>",
        encoding="utf-8"
    )
    mock_wp_res = {"success": True, "id": 9999, "link": "https://tech-tips.ct.ws/2026/09/mock-publish-test/"}

    try:
        with patch("dashboard.routes.publish._wp_publish", return_value=mock_wp_res):
            resp = client.post("/api/publish", json={"filename": "2026-09-18_mock-publish-test.md"})
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            assert data["post_id"] == 9999
            assert "tech-tips.ct.ws" in data["url"]
    finally:
        if test_article.exists():
            test_article.unlink()
