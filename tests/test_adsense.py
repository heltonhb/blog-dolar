# -*- coding: utf-8 -*-
"""Tests for the AdSense page and status API (and removal of old ad tabs)."""

PUB_ID = "ca-pub-6258036451330976"

HOME_HTML = f"""<html><head>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={PUB_ID}" crossorigin="anonymous"></script>
<meta name="google-adsense-account" content="{PUB_ID}">
</head><body>ok</body></html>"""

ADS_TXT = "google.com, pub-6258036451330976, DIRECT, f08c47fec0942fa0\n"


def test_adsense_page_renders(client):
    """The AdSense tab renders."""
    resp = client.get("/adsense")
    assert resp.status_code == 200
    assert "AdSense" in resp.get_data(as_text=True)


def test_old_ad_tabs_are_gone(client):
    """AdCash and Adsterra page routes no longer exist."""
    assert client.get("/adcash").status_code == 404
    assert client.get("/adsterra").status_code == 404


def test_sidebar_links(client):
    """Sidebar points at AdSense, not at the removed tabs."""
    resp = client.get("/")
    html = resp.get_data(as_text=True)
    assert 'href="/adsense"' in html
    assert 'href="/adcash"' not in html
    assert 'href="/adsterra"' not in html


def test_adsense_status_ok(client, monkeypatch):
    """Status API reports every check passing when the site serves the tag."""

    def fake_fetch(path):
        return 200, HOME_HTML if path == "/" else ADS_TXT, ""

    monkeypatch.setattr("dashboard.routes.adsense._fetch", fake_fetch)

    resp = client.get("/api/adsense/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["publisher_id"] == PUB_ID
    assert data["all_ok"] is True
    assert len(data["checks"]) == 5
    assert all(c["ok"] for c in data["checks"])


def test_adsense_status_reports_missing_tag(client, monkeypatch):
    """Status API flags a home page without the AdSense tag."""

    def fake_fetch(path):
        return 200, "<html><body>sem tag</body></html>" if path == "/" else "", ""

    monkeypatch.setattr("dashboard.routes.adsense._fetch", fake_fetch)

    resp = client.get("/api/adsense/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["all_ok"] is False
    by_key = {c["key"]: c for c in data["checks"]}
    assert by_key["home_script"]["ok"] is False
    assert by_key["ads_txt"]["ok"] is False
