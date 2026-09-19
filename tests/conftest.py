# -*- coding: utf-8 -*-
"""Pytest fixtures for the dashboard tests."""
import os
import sys
from pathlib import Path

import pytest

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app():
    """Create application for testing."""
    from dashboard import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create authenticated test client by default."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["authenticated"] = True
    return c


@pytest.fixture
def unauth_client(app):
    """Create unauthenticated test client."""
    return app.test_client()
