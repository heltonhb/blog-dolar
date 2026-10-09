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
    mock_wp_res = {"success": True, "id": 9999, "link": "https://techtips.dpdns.org/2026/09/mock-publish-test/"}

    try:
        with patch("dashboard.routes.publish._wp_publish", return_value=mock_wp_res):
            resp = client.post("/api/publish", json={"filename": "2026-09-18_mock-publish-test.md"})
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            assert data["post_id"] == 9999
            assert "techtips.dpdns.org" in data["url"]
    finally:
        if test_article.exists():
            test_article.unlink()


def test_get_ssl_context_loads_certs():
    """Verify that SSL context is created and valid."""
    from dashboard.services.wordpress import _get_ssl_context

    ctx = _get_ssl_context()
    assert ctx is not False


def test_get_ssl_context_disabled_via_env(monkeypatch):
    """Verify WP_VERIFY_SSL=false disables SSL verification."""
    from dashboard.services.wordpress import _get_ssl_context

    monkeypatch.setenv("WP_VERIFY_SSL", "false")
    ctx = _get_ssl_context()
    assert ctx is False


def test_wp_publish_auto_injects_affiliate_and_quick_picks(monkeypatch):
    """Verify _wp_publish injects disclosure, quick picks, and cards if mapped and not yet present."""
    from dashboard.services.wordpress import _wp_publish

    monkeypatch.setenv("AMAZON_ASSOCIATE_TAG", "testauto-20")
    monkeypatch.setenv("WP_USER", "mockuser")
    monkeypatch.setenv("WP_APP_PASSWORD", "mockpass")

    captured = {}

    class MockResp:
        status_code = 201
        def json(self):
            return {"id": 101, "link": "https://techtips.dpdns.org/post", "status": "publish"}

    class MockClient:
        def post(self, url, auth=None, json=None):
            nonlocal captured
            captured["payload"] = json
            return MockResp()

    monkeypatch.setattr("dashboard.services.wordpress._antibot_session", lambda site_url: MockClient())

    article = {
        "title": "Top 5 Portable Power Banks",
        "slug": "top-5-best-portable-power-banks-in-2026",
        "content": "<p>Intro</p><h2>Anker Prime 27,650mAh</h2><p>Great power bank</p><h2>Conclusion</h2><p>End</p>",
        "meta_description": "Best power banks",
    }

    result = _wp_publish(article)
    assert result["success"] is True
    content = captured["payload"]["content"]
    assert "tech-affiliate-disclosure" in content
    assert "tech-quick-picks" in content
    assert "tech-affiliate-card" in content
    assert "tag=testauto-20" in content


def test_wp_publish_with_custom_products(monkeypatch):
    """Verify _wp_publish saves custom products and injects monetization."""
    from dashboard.services.wordpress import _wp_publish

    monkeypatch.setenv("AMAZON_ASSOCIATE_TAG", "customtag-20")
    monkeypatch.setenv("WP_USER", "mockuser")
    monkeypatch.setenv("WP_APP_PASSWORD", "mockpass")

    captured = {}

    class MockResp:
        status_code = 201
        def json(self):
            return {"id": 202, "link": "https://techtips.dpdns.org/custom-post", "status": "publish"}

    class MockClient:
        def post(self, url, auth=None, json=None):
            nonlocal captured
            captured["payload"] = json
            return MockResp()

    monkeypatch.setattr("dashboard.services.wordpress._antibot_session", lambda site_url: MockClient())

    custom_slug = "best-desk-accessories-2026"
    custom_products = [
        {
            "title": "BenQ ScreenBar Halo",
            "subtitle": "Monitor light bar with wireless controller and back light.",
            "search_query": "BenQ ScreenBar Halo",
            "badge": "BEST LIGHT BAR",
            "after_heading": "BenQ ScreenBar",
            "specs": ["Auto-dimming", "No screen glare", "Curved monitor compatible"],
        },
        {
            "title": "Grovemade Wool Felt Desk Mat",
            "subtitle": "Premium merino wool felt desk pad for workspace organization.",
            "search_query": "Grovemade Wool Felt Desk Mat",
            "badge": "BEST DESK PAD",
            "after_heading": "Grovemade Desk Mat",
            "specs": ["Natural merino wool", "Anti-slip backing", "Multiple sizes"],
        },
    ]

    article = {
        "title": "Best Desk Accessories 2026",
        "slug": custom_slug,
        "content": "<p>Desk accessories intro</p><h2>BenQ ScreenBar</h2><p>Review light</p><h2>Grovemade Desk Mat</h2><p>Review mat</p><h2>Conclusion</h2><p>Verdict</p>",
        "meta_description": "Desk setup guide",
        "products": custom_products,
    }

    result = _wp_publish(article)
    assert result["success"] is True
    content = captured["payload"]["content"]
    assert "tech-affiliate-disclosure" in content
    assert "tech-quick-picks" in content
    assert "BenQ ScreenBar Halo" in content
    assert "Grovemade Wool Felt Desk Mat" in content
    assert "tag=customtag-20" in content


