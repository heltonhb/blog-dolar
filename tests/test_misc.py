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
            "link": "https://techtips.dpdns.org/2026/09/hello-world-post/",
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


def test_sitemap_uses_canonical_permalinks_not_query_strings(client):
    """URLs must be /slug/, not /?p=slug.

    The old implementation emitted ``/?p={slug}``, which is wrong under pretty
    permalinks, and it fed the raw markdown filename in — including the
    ``YYYY-MM-DD_`` prefix, producing URLs that 404.
    """
    resp = client.get("/sitemap.xml")
    content = resp.get_data(as_text=True)
    assert "?p=" not in content, "query-string permalinks are not canonical"
    # No date prefix may leak into a URL path.
    import re
    for loc in re.findall(r"<loc>([^<]+)</loc>", content):
        assert not re.search(r"/\d{4}-\d{2}-\d{2}_", loc), f"date prefix leaked: {loc}"


def test_sitemap_escapes_xml_entities(client):
    """A URL containing & or < must not break the XML document."""
    from unittest.mock import patch

    entries = [{"loc": "https://ex.test/a&b/<c>", "lastmod": "2026-01-01"}]
    with patch("dashboard.routes.misc._sitemap_entries_from_wp", return_value=entries):
        resp = client.get("/sitemap.xml")
    content = resp.get_data(as_text=True)
    assert "&amp;" in content
    assert "&lt;" in content
    assert "<c>" not in content


def test_sitemap_falls_back_to_local_articles(client, monkeypatch):
    """With WordPress unreachable, local articles still produce clean URLs."""
    from dashboard.routes import misc

    monkeypatch.setattr(misc, "_sitemap_entries_from_wp", lambda site: [])
    resp = client.get("/sitemap.xml")
    content = resp.get_data(as_text=True)
    assert "<urlset" in content
    assert "?p=" not in content


def test_posts_route_returns_data(client, monkeypatch):
    """Regression: /api/posts must not silently return [] on an internal error.

    A removed import once made this raise NameError inside the route, and the
    blanket ``except Exception`` swallowed it into an empty list — which reads
    as "no posts published".
    """
    from unittest.mock import MagicMock, patch

    monkeypatch.setenv("WP_USER", "u")
    monkeypatch.setenv("WP_APP_PASSWORD", "p")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{
        "id": 1,
        "title": {"rendered": "T"},
        "slug": "s",
        "date": "2026-09-18T12:00:00",
        "link": "https://ex.test/s/",
        "content": {"rendered": "<p>body</p>"},
    }]
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    with patch("dashboard.routes.misc._antibot_session", return_value=mock_client):
        data = client.get("/api/posts").get_json()
    assert len(data) == 1
    assert data[0]["content"] == "body", "HTML must be stripped, not dropped"
