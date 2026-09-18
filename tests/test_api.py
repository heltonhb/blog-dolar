# -*- coding: utf-8 -*-
"""Tests for API endpoints."""
import sys
from pathlib import Path

# Use existing app.py for tests
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))


def test_api_health():
    """Test health check endpoint."""
    import app
    with app.app.test_client() as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data


def test_login_without_password():
    """Test login when no password is set."""
    import app
    with app.app.test_client() as client:
        response = client.get("/login")
        assert response.status_code == 200


def test_index_page():
    """Test main dashboard page (redirects to /login if no session)."""
    import app
    with app.app.test_client() as client:
        response = client.get("/")
        assert response.status_code in (200, 302)
