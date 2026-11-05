"""Rewrite the year-stuffed body of post 26 and drop 2024 from the slug."""

import json
import re
import os
import pathlib
import sys

from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dashboard.services.wordpress import _antibot_session

load_dotenv()
BASE = "https://techtips.dpdns.org"
BACKUP = pathlib.Path(__file__).resolve().parents[1] / "cache" / "backup_datafix"
PID = 26

# Ordered, one-shot replacements: the same exact-match phrase was pasted eight
# times, which reads as keyword stuffing. Keep it verbatim in the opening
# paragraph and the H2 (where a search phrase legitimately belongs) and vary
# the rest. The 2024 in the intro is rewritten as history, not as currency.
REPLACEMENTS = [
    (
        "In 2024, your users are browsing from a dizzying array of devices",
        "Since 2024 your users have been browsing from a dizzying array of devices",
    ),
    (
        "Implementing effective <strong>responsive web design best practices 2024</strong> is no longer a luxury",
        "Applying today's <strong>responsive web design best practices</strong> is no longer a luxury",
    ),
    (
        "<h2>Responsive Web Design Best Practices 2024: Key Strategies</h2>",
        "<h2>Responsive Web Design Best Practices 2026: Key Strategies</h2>",
    ),
    (
        "on older frameworks that use floats, it is time for an upgrade. <strong>Responsive web design best practices 2024</strong> dictate",
        "on older frameworks that use floats, it is time for an upgrade. Current <strong>responsive web design best practices</strong> dictate",
    ),
    (
        "As part of our <strong>responsive web design best practices 2024</strong>, performance is non-negotiable.",
        "Performance is non-negotiable under any serious set of <strong>responsive design best practices</strong>.",
    ),
    (
        "<strong>Responsive web design best practices 2024</strong> include rigorous testing",
        "Today's <strong>responsive design best practices</strong> include rigorous testing",
    ),
    (
        "While they are great for quick checks, <strong>responsive web design best practices 2024</strong> require real-world testing.",
        "While they are great for quick checks, nothing replaces the real-world testing that modern <strong>responsive design practice</strong> demands.",
    ),
    (
        "This is the next frontier of <strong>responsive web design best practices 2024</strong>",
        "This is the next frontier of <strong>responsive web design best practices</strong>",
    ),
    (
        "Start auditing your site today using these <strong>responsive web design best practices 2024</strong>",
        "Start auditing your site today using the <strong>responsive web design best practices</strong> outlined above",
    ),
    (
        "</p>\n<p></p>\n\n<!-- internal-links -->",
        "\n\n<!-- internal-links -->",
    ),
]

EXCERPT_REPLACEMENTS = [
    (
        "Master responsive web design best practices 2024.",
        "Master responsive web design best practices 2026.",
    ),
]

NEW_SLUG = "responsive-web-design-best-practices-2026"


def rewrite(text, replacements):
    for old, new in replacements:
        if old not in text:
            raise SystemExit(f"pattern not found, aborting:\n{old[:90]}")
        text = text.replace(old, new, 1)
    return text


def main():
    apply = "--apply" in sys.argv
    post = json.loads((BACKUP / f"post_{PID}.json").read_text())
    content = rewrite(post["content"]["raw"], REPLACEMENTS)
    excerpt = rewrite(post["excerpt"]["raw"], EXCERPT_REPLACEMENTS)

    # "Since 2024 your users have been browsing..." is a deliberate historical
    # reference, so a bare 2024 is still allowed there. What must be gone is
    # the year being used as currency, i.e. the exact-match search phrase.
    stale = re.findall(r"responsive web design best practices 2024", content, re.I)
    assert not stale, f"frase-chave com 2024 sobrou: {stale}"
    assert content.count("2024") == 1, f"2024 sobrou: {content.count('2024')}"
    assert "2024" not in excerpt, "2024 sobrou no excerpt"

    old_url = f"{BASE}/2026/09/19/{post['slug']}/"
    c = _antibot_session(BASE)
    c.auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])
    r = c.get(f"{BASE}/wp-json/wp/v2/posts/{PID}")
    print(f"URL antiga: {old_url}")
    print(f"URL nova  : {BASE}/2026/09/19/{NEW_SLUG}/")
    print(f"diff corpo: {len(post['content']['raw'])} -> {len(content)} chars")

    if not apply:
        print("DRY-RUN: nada enviado")
        return

    r = c.post(
        f"{BASE}/wp-json/wp/v2/posts/{PID}",
        json={
            "content": content,
            "excerpt": excerpt,
            "slug": NEW_SLUG,
        },
        params={"context": "edit"},
    )
    print(f"PUT -> {r.status_code}")
    if r.status_code != 200:
        print(r.text[:800])
        return
    got = r.json()
    print(f"slug: {got['slug']} | status: {got['status']} | date: {got['date']}")
    print(f"link: {got['link']}")
    assert got["slug"] == NEW_SLUG
    assert not re.search(
        r"responsive web design best practices 2024", got["content"]["raw"], re.I
    ), "frase-chave com 2024 sobreviveu no corpo"
    assert got["content"]["raw"].count("2024") == 1, "2024 inesperado no corpo"


if __name__ == "__main__":
    main()