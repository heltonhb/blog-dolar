# -*- coding: utf-8 -*-
"""Date/year awareness helpers for content generation.

Kept dependency-free (stdlib only) so both the Flask dashboard and the
standalone ``scripts/gerar_artigos.py`` CLI can import it without pulling in
an application context.

The LLM has no notion of "today" unless we tell it, so every generation prompt
must carry the current date. Otherwise it free-associates a plausible-looking
year and bakes stale years into titles and body copy.
"""

import re
from datetime import datetime

# A 4-digit run preceded by "$" is a price, and one preceded by "-" or "/" is
# the upper bound of a range ("1500-2000 words"). Both must survive: buyer-intent
# keywords are literally shaped like "best [gear] under $2000 in 2026", so
# rewriting prices would corrupt the commercial keyword. The cost is that an
# explicit year range ("2020-2024") is left untouched, which is the safer
# failure mode since it never silently rewrites a number the user typed.
_YEAR_RE = re.compile(r"(?<![$-/])\b(?:19|20)\d{2}\b")


def current_year() -> int:
    """Return the current calendar year."""
    return datetime.now().year


def current_date_iso() -> str:
    """Return today's date as ``YYYY-MM-DD``."""
    return datetime.now().strftime("%Y-%m-%d")


def normalize_year(text: str) -> str:
    """Replace every 4-digit year in ``text`` with the current year.

    Used on keywords and idea titles *before* they reach a prompt, so a stale
    year already persisted in the ideas database stops propagating into new
    articles. Article bodies are never passed through this function, since
    they may legitimately mention historical years.

    Monetary amounts (``$2000``) are left alone.
    """
    if not text:
        return text
    year = str(current_year())
    return _YEAR_RE.sub(year, text)


def date_prompt_block() -> str:
    """Return the date instructions to embed in a generation prompt."""
    return (
        f"Today's date is {current_date_iso()} (year {current_year()}). "
        "Only reference a year if the target keyword already contains one, and "
        "then use exactly the year given in the keyword. Never invent, guess or "
        "reuse a year from your training data."
    )
