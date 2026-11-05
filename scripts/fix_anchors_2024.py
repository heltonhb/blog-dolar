"""Refresh stale anchor text in the internal-links block.

`scripts/internal_links.py --apply` would recompute the similarity plan for
every post and reshuffle Related Articles site-wide. Here the titles of three
posts changed, so the only thing wrong is the anchor *text* of the links that
point at them. Rewrite just that, inside the existing block.
"""

import html
import os
import pathlib
import re
import sys

from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dashboard.services.wordpress import _antibot_session

load_dotenv()
BASE = "https://techtips.dpdns.org"
BACKUP = pathlib.Path(__file__).resolve().parents[1] / "cache" / "backup_datafix"

BLOCK_RE = re.compile(
    r"<!-- internal-links -->.*?<!-- /internal-links -->", re.DOTALL
)


def main():
    apply = "--apply" in sys.argv
    c = _antibot_session(BASE)
    c.auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])

    # Canonical titles + permalink tails, straight from the API.
    canon = {}
    for pid in (208, 214, 237):
        data = c.get(
            f"{BASE}/wp-json/wp/v2/posts/{pid}?_fields=id,link,title"
        ).json()
        canon[pid] = (
            html.unescape(data["title"]["rendered"]),
            data["link"].rstrip("/").rsplit("/", 1)[-1],
        )

    posts = c.get(
        f"{BASE}/wp-json/wp/v2/posts?per_page=100&context=edit&_fields=id,content"
    ).json()

    touched = 0
    for p in posts:
        body = p["content"]["raw"]
        new = body
        for pid, (title, tail) in canon.items():
            # Any anchor whose href points at this post, whatever the text says.
            new = re.sub(
                r'(<a href="[^"]*/' + re.escape(tail) + r'/">)(.*?)(</a>)',
                lambda m: m.group(1) + title + m.group(3),
                new,
                flags=re.DOTALL,
            )
        if new == body:
            continue

        block = BLOCK_RE.search(new)
        touched += 1
        changed = [
            html.unescape(re.sub("<[^>]+>", "", li))
            for li in re.findall(r"<li>(.*?)</li>", block.group(0), re.DOTALL)
        ]
        print(f"== post {p['id']}")
        for line in changed:
            print(f"   - {line}")
        if not apply:
            continue
        r = c.post(
            f"{BASE}/wp-json/wp/v2/posts/{p['id']}",
            json={"content": new},
            params={"context": "edit"},
        )
        print(f"   PUT -> {r.status_code}")
        if r.status_code != 200:
            print(r.text[:300])

    print(f"\n{touched} post(s) com ancora desatualizada")
    if not apply:
        print("DRY-RUN: nada enviado")


if __name__ == "__main__":
    main()