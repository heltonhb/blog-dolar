# -*- coding: utf-8 -*-
"""Tests for Articles API and article services."""
import json
from pathlib import Path
from unittest.mock import patch

from dashboard.services.articles import _extract_article_info


def test_list_articles(client):
    """Test /api/articles/list returns a list."""
    resp = client.get("/api/articles/list")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_extract_article_info(tmp_path):
    """Test _extract_article_info parses frontmatter and body."""
    md_file = tmp_path / "2026-09-18_test-article.md"
    content = """---
title: Test Article Title
slug: test-article
meta_description: A test meta description.
tags: ["tech", "testing"]
---

<h2>Section One</h2>
<p>This is a paragraph with more than a few words to test extraction.</p>
<h3>Sub Section</h3>
<p>Another paragraph testing content.</p>
"""
    md_file.write_text(content, encoding="utf-8")

    info = _extract_article_info(md_file)
    assert info["title"] == "Test Article Title"
    assert info["slug"] == "test-article"
    assert info["meta_description"] == "A test meta description."
    assert "tech" in info["tags"]
    assert len(info["keywords"]) >= 2
    assert "Section One" in info["keywords"]


def test_delete_article_validation(client):
    """Test validation when deleting articles."""
    # Non-existent
    resp = client.delete("/api/articles/delete/non_existent_article_xyz.md")
    assert resp.status_code == 404

    # Non-md file
    resp = client.delete("/api/articles/delete/invalid_file.txt")
    assert resp.status_code == 400


def test_generate_and_verify_article_mocked(client):
    """Test generating an article with mocked Gemini call and verifying it."""
    mock_article = {
        "title": "Pytest Guide for Developers",
        "slug": "pytest-guide-for-developers",
        "meta_description": "Comprehensive guide to testing with pytest in Python.",
        "content": (
            "<h2>Introduction to Pytest</h2><p>" + ("pytest is great for python testing " * 50) + "</p>"
            "<h2>Advanced Features</h2><p>" + ("fixtures and parameterization are awesome " * 50) + "</p>"
            "<h3>Best Practices</h3><p>" + ("keep tests isolated and fast " * 50) + "</p>"
            "<p><a href='/tech-tips/article'>Related Post</a></p>"
            "<img src='test.jpg' alt='test'>"
        ),
        "tags": ["python", "testing", "pytest"]
    }

    with patch("dashboard.routes.articles._gemini_call", return_value=json.dumps(mock_article)):
        gen_resp = client.post("/api/generate", json={"keyword": "pytest guide"})
        assert gen_resp.status_code == 200
        gen_data = gen_resp.get_json()
        assert gen_data["success"] is True
        filename = gen_data["filename"]

        try:
            # Now verify the generated article
            ver_resp = client.post("/api/verify", json={"filename": filename, "use_ai": False})
            assert ver_resp.status_code == 200
            ver_data = ver_resp.get_json()
            assert ver_data["success"] is True
            assert ver_data["result"]["score"] >= 70
            assert ver_data["result"]["status"] == "Aprovado"
        finally:
            # Clean up generated test file
            del_resp = client.delete(f"/api/articles/delete/{filename}")
            assert del_resp.status_code == 200
