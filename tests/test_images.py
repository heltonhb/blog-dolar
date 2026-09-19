# -*- coding: utf-8 -*-
"""Tests for Images API."""
from pathlib import Path
from unittest.mock import patch

from dashboard.services.helpers import _images_dir


def test_list_images(client):
    """Test listing generated images."""
    resp = client.get("/api/images/list")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_generate_image_mocked(client):
    """Test generating an image with mocked generator."""
    mock_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    with patch("dashboard.routes.images.generate_image", return_value=(mock_bytes, "pollinations")):
        resp = client.post("/api/images/generate", json={
            "prompt": "futuristic tech gadget macro shot",
            "filename": "test-gen-img.png",
            "usage": "square"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["filename"] == "test-gen-img.png"

        # Verify file on disk and clean up
        img_file = _images_dir() / "test-gen-img.png"
        assert img_file.exists()

        del_resp = client.delete("/api/images/delete/test-gen-img.png")
        assert del_resp.status_code == 200
        assert not img_file.exists()


def test_delete_nonexistent_image(client):
    """Test deleting non-existent image returns 404."""
    resp = client.delete("/api/images/delete/non_existent_img_12345.png")
    assert resp.status_code == 404


def test_preview_prompt_mocked(client, tmp_path):
    """Test previewing prompt for an article."""
    from dashboard.services.helpers import _articles_dir
    test_article = _articles_dir() / "2026-09-18_preview-test.md"
    test_article.write_text(
        "---\ntitle: Preview Prompt Title\nslug: preview-test\nmeta_description: Test meta\ntags: ['tech']\n---\n\n<p>Body</p>",
        encoding="utf-8"
    )
    try:
        resp = client.post("/api/images/preview_prompt", json={
            "filename": "2026-09-18_preview-test.md",
            "usage": "pinterest"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "prompt" in data
    finally:
        if test_article.exists():
            test_article.unlink()
