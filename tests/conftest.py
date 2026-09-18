# -*- coding: utf-8 -*-
"""Pytest configuration and shared fixtures."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))


@pytest.fixture
def app_factory():
    """Return app for testing."""
    import app
    return app.app
