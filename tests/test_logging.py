# -*- coding: utf-8 -*-
"""Tests for logging module."""
from pathlib import Path


def test_json_formatter():
    """Test JSON log formatter."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))
    
    from services.logging import JSONFormatter
    import logging
    
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    result = formatter.format(record)
    assert "Test message" in result
    assert "timestamp" in result
    assert "level" in result
