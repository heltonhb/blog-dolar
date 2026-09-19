# -*- coding: utf-8 -*-
"""Tests for API endpoints."""


def test_health_endpoint(client):
    """Test /api/health returns 200 with status ok."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "dns" in data


def test_login_page_loads(client):
    """Test /login page loads with GET."""
    resp = client.get("/login")
    assert resp.status_code == 200


def test_unauthenticated_redirect(unauth_client, monkeypatch):
    """Test that pages redirect to login when not authenticated."""
    monkeypatch.setenv("DASHBOARD_PASSWORD", "test123")
    resp = unauth_client.get("/")
    # Should redirect to login
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("Location", "")


def test_logout_clears_session(client):
    """Test /logout clears session and redirects."""
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("Location", "")
