import json
import pathlib
import os
import re
import sys

from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dashboard.services.wordpress import _antibot_session

load_dotenv()
BASE = "https://techtips.dpdns.org"
BACKUP = pathlib.Path(__file__).resolve().parents[1] / "cache" / "backup_datafix"
YEAR_RE = re.compile(r"\b2024\b")

DRY = "--apply" not in sys.argv


def client():
    c = _antibot_session(BASE)
    c.auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])
    return c


def main():
    c = client()
    for pid in (208, 214, 237):
        post = json.loads((BACKUP / f"post_{pid}.json").read_text())
        old_title = post["title"]["raw"]
        new_title = YEAR_RE.sub("2026", old_title)
        body = post["content"]["raw"]
        new_body = YEAR_RE.sub("2026", body)
        changes = []
        if new_title != old_title:
            changes.append(f"title: {old_title!r} -> {new_title!r}")
        if new_body != body:
            changes.append(f"content: {len(body)} -> {len(new_body)} chars")
        payload = {}
        if new_title != old_title:
            payload["title"] = new_title
        if new_body != body:
            payload["content"] = new_body
        print(f"\n== post {pid}")
        for ch in changes:
            print(f"   {ch}")
        if not changes:
            print("   nada a corrigir")
            continue
        if DRY:
            print("   DRY-RUN: nada enviado")
            continue
        r = c.post(
            f"{BASE}/wp-json/wp/v2/posts/{pid}",
            json=payload,
            params={"context": "edit"},
        )
        print(f"   PUT -> {r.status_code}")
        if r.status_code != 200:
            print(r.text[:500])
            continue
        got = r.json()
        print(f"   slug agora: {got['slug']} (era {post['slug']})")
        assert got["slug"] == post["slug"], "slug mudou! URL quebrada"
        assert "2024" not in got["title"]["raw"], "2024 sobrou no titulo"
        print("   OK")

        new_alt = YEAR_RE.sub("2026", new_title)
        if new_alt != old_title:
            mr = c.post(
                f"{BASE}/wp-json/wp/v2/media/{got['featured_media']}",
                json={"alt_text": new_alt},
                params={"context": "edit"},
            )
            print(f"   media {got['featured_media']} alt -> {mr.status_code}")
            if mr.status_code == 200:
                print(f"      alt: {mr.json()['alt_text']}")
            else:
                print(mr.text[:300])


if __name__ == "__main__":
    main()