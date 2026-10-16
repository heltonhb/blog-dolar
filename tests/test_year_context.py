# -*- coding: utf-8 -*-
"""Regression tests for date/year handling in generated content.

Without an explicit current date in the prompt, the model free-associates a
year and bakes stale ones ("...in 2024") into titles and body copy. These tests
pin down both halves of the fix: the prompt must carry today's date, and any
year already present in a keyword or idea must be refreshed.
"""

import json
from datetime import datetime
from unittest.mock import patch

from dashboard.services.year_context import (
    current_year,
    date_prompt_block,
    normalize_year,
)


# ---------------------------------------------------------------------------
#  normalize_year
# ---------------------------------------------------------------------------

def test_normalize_year_replaces_stale_year():
    """A stale year in a keyword is rewritten to the current year."""
    result = normalize_year("best monitors for work from home in 2024")
    assert result == f"best monitors for work from home in {current_year()}"
    assert "2024" not in result


def test_normalize_year_replaces_every_occurrence():
    """All stale years are replaced, not just the first."""
    result = normalize_year("2024 guide, updated 2025")
    year = str(current_year())
    assert "2024" not in result
    assert "2025" not in result
    assert result == f"{year} guide, updated {year}"


def test_normalize_year_leaves_text_without_year_untouched():
    """Text with no 4-digit year is returned unchanged."""
    text = "best noise-canceling headphones for remote work"
    assert normalize_year(text) == text


def test_normalize_year_does_not_touch_prices_or_partial_numbers():
    """Money amounts and numbers that merely contain a year are preserved."""
    for text in ("under $2000", "$1,200 and $99", "the 1500-2000 word guide", "model X2024 Pro"):
        assert normalize_year(text) == text


def test_normalize_year_keeps_price_but_refreshes_year_in_same_keyword():
    """The realistic case: a budget keyword with both a price and a year."""
    result = normalize_year("best monitors under $2000 in 2024")
    assert result == f"best monitors under $2000 in {current_year()}"


def test_normalize_year_handles_empty_input():
    """Empty and None-ish inputs do not raise."""
    assert normalize_year("") == ""
    assert normalize_year(None) is None


# ---------------------------------------------------------------------------
#  date_prompt_block
# ---------------------------------------------------------------------------

def test_date_prompt_block_contains_today():
    """The prompt block carries the real current date."""
    block = date_prompt_block()
    today = datetime.now().strftime("%Y-%m-%d")
    assert today in block
    assert str(current_year()) in block
    assert "Never invent" in block


# ---------------------------------------------------------------------------
#  /api/generate
# ---------------------------------------------------------------------------

def test_generate_prompt_includes_current_date(client):
    """The article prompt tells the model today's date and bans invented years."""
    captured = {}

    mock_article = {
        "title": "Pytest Guide",
        "slug": "pytest-guide",
        "meta_description": "Guide to testing with pytest.",
        "content": "<h2>Intro</h2><p>" + ("pytest testing content " * 60) + "</p>",
        "tags": ["python"],
    }

    def fake_call(prompt):
        captured["prompt"] = prompt
        return json.dumps(mock_article)

    with patch("dashboard.routes.articles._gemini_call", side_effect=fake_call):
        resp = client.post("/api/generate", json={"keyword": "pytest guide"})
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True
        try:
            prompt = captured["prompt"]
            assert datetime.now().strftime("%Y-%m-%d") in prompt
            assert str(current_year()) in prompt
            assert "Never invent" in prompt
        finally:
            client.delete(f"/api/articles/delete/{resp.get_json()['filename']}")


def test_generate_normalizes_stale_year_in_keyword(client):
    """A keyword carrying 2024 reaches the prompt with the current year instead."""
    captured = {}

    mock_article = {
        "title": "Best Monitors",
        "slug": "best-monitors",
        "meta_description": "Monitors for work.",
        "content": "<h2>Intro</h2><p>" + ("monitor content " * 60) + "</p>",
        "tags": ["monitors"],
    }

    def fake_call(prompt):
        captured["prompt"] = prompt
        return json.dumps(mock_article)

    with patch("dashboard.routes.articles._gemini_call", side_effect=fake_call):
        resp = client.post(
            "/api/generate", json={"keyword": "best monitors for work from home in 2024"}
        )
        assert resp.status_code == 200
        try:
            prompt = captured["prompt"]
            assert "2024" not in prompt
            assert str(current_year()) in prompt
        finally:
            client.delete(f"/api/articles/delete/{resp.get_json()['filename']}")


# ---------------------------------------------------------------------------
#  Ideas
# ---------------------------------------------------------------------------

def test_buyer_intent_ideas_have_no_stale_year():
    """Buyer-intent ideas are normalized and the prompt year is not hardcoded."""
    year = str(current_year())
    captured = {}

    mock_ideas = [
        {"title": "Best Headphones for Travel in 2024", "keyword": "best headphones 2024"},
        {"title": "Top 5 Must-Have Accessories", "keyword": "must-have tech accessories"},
    ]

    def fake_call(prompt):
        captured["prompt"] = prompt
        return json.dumps(mock_ideas)

    with patch("dashboard.routes.ideas._gemini_call", side_effect=fake_call):
        from dashboard.routes.ideas import _generate_buyer_intent_ideas

        ideas = _generate_buyer_intent_ideas()

    assert "2024" not in captured["prompt"]
    assert year in captured["prompt"]
    assert ideas[0]["title"] == f"Best Headphones for Travel in {year}"
    assert ideas[0]["keyword"] == f"best headphones {year}"
    assert ideas[1]["keyword"] == "must-have tech accessories"


def test_normalize_ideas_ignores_non_list_payload():
    """A malformed model response does not blow up normalization."""
    from dashboard.routes.ideas import _normalize_ideas

    assert _normalize_ideas({"not": "a list"}) == {"not": "a list"}
    assert _normalize_ideas(None) is None


def test_normalize_ideas_skips_malformed_entries():
    """Non-dict entries and non-string fields pass through untouched."""
    from dashboard.routes.ideas import _normalize_ideas

    result = _normalize_ideas(["a string", {"title": None, "keyword": "plain keyword"}])
    assert result[0] == "a string"
    assert result[1] == {"title": None, "keyword": "plain keyword"}
