# -*- coding: utf-8 -*-
"""Pytest fixtures for the dashboard tests."""
import os
import sys
from pathlib import Path

import pytest

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

TEST_CSRF_TOKEN = "test-csrf-token"


class _CsrfTestClient:
    """Test client wrapper that injects the session CSRF token automatically.

    The dashboard enforces CSRF on every mutating request, so tests exercise
    the real protection path by sending the token as a header (the same way
    the browser does, via the fetch() patch in layout.html).
    """

    def __init__(self, client, token: str):
        self._client = client
        self._token = token

    def _opts(self, kwargs):
        headers = dict(kwargs.pop("headers", None) or {})
        headers.setdefault("X-CSRF-Token", self._token)
        kwargs["headers"] = headers
        return kwargs

    def post(self, *args, **kwargs):
        return self._client.post(*args, **self._opts(kwargs))

    def put(self, *args, **kwargs):
        return self._client.put(*args, **self._opts(kwargs))

    def patch(self, *args, **kwargs):
        return self._client.patch(*args, **self._opts(kwargs))

    def delete(self, *args, **kwargs):
        return self._client.delete(*args, **self._opts(kwargs))

    def __getattr__(self, name):
        return getattr(self._client, name)


@pytest.fixture
def app():
    """Create application for testing."""
    from dashboard import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create authenticated test client by default (CSRF token attached)."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["authenticated"] = True
        sess["_csrf_token"] = TEST_CSRF_TOKEN
    return _CsrfTestClient(c, TEST_CSRF_TOKEN)


@pytest.fixture
def raw_client(app):
    """Authenticated client WITHOUT automatic CSRF injection (security tests)."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["authenticated"] = True
        sess["_csrf_token"] = TEST_CSRF_TOKEN
    return c


@pytest.fixture
def unauth_client(app):
    """Create unauthenticated test client."""
    return app.test_client()
