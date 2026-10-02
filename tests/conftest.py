# -*- coding: utf-8 -*-
"""Pytest fixtures for the dashboard tests."""
import os
import shutil
import sys
from pathlib import Path

import pytest

# Ensure project root is in path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Run the whole suite against a throwaway tree. Previously the suite shared the
# real repository: /api/settings wrote into the production .env (a test key was
# persisted there), and create_app() opened a connection to the production Neon
# database on every fixture — which is why the run took ~4 minutes.
SANDBOX = REPO_ROOT / ".pytest_sandbox"

os.environ["SKIP_DB_INIT"] = "1"
os.environ["SKIP_SCHEDULER"] = "1"


def _build_sandbox() -> None:
    """Copy the fixtures the suite reads into a disposable tree."""
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    (SANDBOX / "dashboard" / "data").mkdir(parents=True)
    (SANDBOX / "dashboard" / "static" / "images").mkdir(parents=True)

    # The suite must NOT depend on the developer's real .env: it is absent on
    # CI, and relying on it made every authenticated test fail there (503 from
    # login_required's fail-closed path). Build a self-contained one instead.
    real_env = REPO_ROOT / ".env"
    seed = SANDBOX / ".env"
    if real_env.exists():
        # Copy through so the real file is never written to, keeping the
        # caller's credentials out of the sandbox.
        shutil.copy(real_env, seed)
    else:
        seed.write_text("", encoding="utf-8")

    # login_required fails closed (503) when no password is configured, so the
    # suite must always provide one to reach any protected route.
    text = seed.read_text(encoding="utf-8")
    if "DASHBOARD_PASSWORD=" not in text:
        text += "DASHBOARD_PASSWORD=test-suite-password\n"
    if "FORCE_HTTPS=" not in text:
        # The sandbox is plain http; a Secure cookie would never be sent back.
        text += "FORCE_HTTPS=0\n"
    seed.write_text(text, encoding="utf-8")

    # Some tests assert against real content (a bridge page resolves a specific
    # published slug). Copy read-only fixtures; nothing writes back to the repo.
    articles = REPO_ROOT / "articles"
    (SANDBOX / "articles").mkdir(parents=True, exist_ok=True)
    if articles.exists():
        for md in articles.glob("*.md"):
            shutil.copy(md, SANDBOX / "articles" / md.name)

    for png in (REPO_ROOT / "dashboard" / "static" / "images").glob("*.png"):
        shutil.copy(png, SANDBOX / "dashboard" / "static" / "images" / png.name)

    # The runner resolves its allow-listed scripts under <root>/scripts, and the
    # AdSense status check reads the mu-plugin source from there.
    (SANDBOX / "scripts").mkdir(parents=True, exist_ok=True)
    for item in (REPO_ROOT / "scripts").iterdir():
        if item.is_file():
            shutil.copy(item, SANDBOX / "scripts" / item.name)


_build_sandbox()
os.environ["BLOG_DOLAR_ROOT"] = str(SANDBOX)


@pytest.fixture(scope="session", autouse=True)
def _cleanup_sandbox():
    yield
    shutil.rmtree(SANDBOX, ignore_errors=True)
    os.environ.pop("BLOG_DOLAR_ROOT", None)


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
