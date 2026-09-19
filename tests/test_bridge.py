# -*- coding: utf-8 -*-
"""Tests for Pinterest Safe Bridge Page functionality."""
from unittest.mock import MagicMock, patch

from dashboard.services.bridge import (
    extract_slug_from_url_or_slug,
    get_bridge_base_url,
    get_bridge_url,
    is_bridge_enabled,
    resolve_article_for_bridge,
)


def test_extract_slug_from_url_or_slug():
    """Test extracting clean slugs from various URL formats and strings."""
    assert extract_slug_from_url_or_slug("cool-laptops-2026") == "cool-laptops-2026"
    assert extract_slug_from_url_or_slug("https://tech-tips.ct.ws/?p=my-article-slug") == "my-article-slug"
    assert extract_slug_from_url_or_slug("https://tech-tips.ct.ws/2026/09/03/best-monitors/") == "best-monitors"
    assert extract_slug_from_url_or_slug("https://tech-tips.ct.ws/responsive-web-design-best-practices-2024/") == "responsive-web-design-best-practices-2024"
    assert extract_slug_from_url_or_slug("") == ""


def test_get_bridge_url(monkeypatch):
    """Test generating bridge URLs with custom and default base URLs."""
    monkeypatch.setenv("BRIDGE_BASE_URL", "https://blog-dolar-dashboard.onrender.com")
    url = get_bridge_url("responsive-web-design-best-practices-2024")
    assert url == "https://blog-dolar-dashboard.onrender.com/p/responsive-web-design-best-practices-2024"


def test_bridge_page_renders_with_fallback_slug(client):
    """Test that visiting a slug without a local markdown file generates a clean fallback bridge page."""
    resp = client.get("/p/responsive-web-design-best-practices-2024")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Responsive Web Design Best Practices 2024" in html
    assert 'property="og:title"' in html
    assert 'property="og:image"' in html
    assert 'name="p:domain_verify"' in html
    assert "https://tech-tips.ct.ws/responsive-web-design-best-practices-2024/" in html
    assert "Acessar Artigo Completo" in html


def test_bridge_page_renders_with_existing_article(client):
    """Test that visiting an existing article slug extracts markdown metadata and highlights."""
    resp = client.get("/p/top-5-best-portable-power-banks-in-2026")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Power Banks" in html
    assert 'rel="canonical"' in html
    assert "Acessar Artigo Completo" in html


def test_bridge_route_alias(client):
    """Test that /bridge/<slug> is an alias to /p/<slug>."""
    resp = client.get("/bridge/responsive-web-design-best-practices-2024")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Responsive Web Design Best Practices 2024" in html


def test_bridge_api_endpoints(client):
    """Test bridge API endpoints for authenticated users."""
    resp = client.get("/api/bridge/url?slug=test-gadget")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "/p/test-gadget" in data["bridge_url"]

    resp_info = client.get("/api/bridge/info/test-gadget")
    assert resp_info.status_code == 200
    info_data = resp_info.get_json()
    assert info_data["success"] is True
    assert info_data["article"]["slug"] == "test-gadget"
