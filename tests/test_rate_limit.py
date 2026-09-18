# -*- coding: utf-8 -*-
"""Tests for rate limiting module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))


def test_rate_limit_installed():
    """Test flask-limiter is installed."""
    import flask_limiter
    assert flask_limiter is not None

