#!/usr/bin/env python3
"""Busca posts do WordPress pelo slug via REST (com app password).

A REST da InfinityFree fica atrás do mesmo anti-bot AES das páginas:
o cookie __test é resolvido UMA vez (antibot.obter_cookie) e reusado.
"""
import base64
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from antibot import SITE, get, obter_cookie, solve_challenge  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")


def _auth_header() -> dict:
    user = os.getenv("WP_USER", "")
    pw = os.getenv("WP_APP_PASSWORD", "")
    if user and pw:
        cred = base64.b64encode(f"{user}:{pw}".encode()).decode()
        return {"Authorization": f"Basic {cred}"}
    return {}


def _rest_get(url: str) -> str:
    """GET na REST atravessando o anti-bot com cookie cacheado."""
    import urllib.error
    import urllib.request

    def _abre(extra: dict | None = None) -> str:
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        headers.update(_auth_header())
        if extra:
            headers.update(extra)
        req = urllib.request.Request(url, headers=headers)
        try:
            return urllib.request.urlopen(req, timeout=30).read().decode()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"REST respondeu {e.code}") from e

    raw = _abre()
    if "toNumbers" in raw:  # challenge AES embutido num HTTP 200
        cookie = obter_cookie()
        if not cookie:
            raise RuntimeError("anti-bot: challenge não resolvido")
        raw = _abre({"Cookie": f"__test={cookie}"})
    if raw.strip().startswith("<"):
        raise RuntimeError("anti-bot bloqueou a REST API mesmo com cookie")
    return raw


def fetch_post_by_slug(slug: str) -> dict | None:
    """Retorna {title, link, slug, content_html} do post vivo no WP."""
    url = (
        f"{SITE}/wp-json/wp/v2/posts?slug={slug}"
        "&_fields=title,link,slug,content"
    )
    raw = _rest_get(url)
    posts = json.loads(raw)
    if not posts:
        return None
    p = posts[0]
    return {
        "title": p["title"]["rendered"],
        "link": p["link"],
        "slug": p["slug"],
        "content_html": p["content"]["rendered"],
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uso: fetch_wp_post.py <slug>")
        sys.exit(1)
    post = fetch_post_by_slug(sys.argv[1])
    if post:
        print(json.dumps(
            {k: (v[:100] + "…" if k == "content_html" else v)
             for k, v in post.items()},
            indent=2, ensure_ascii=False,
        ))
    else:
        print("post não encontrado")
