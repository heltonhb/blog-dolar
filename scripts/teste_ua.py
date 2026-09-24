#!/usr/bin/env python3
"""Isola a variável: PUT com cookie fresco + UA custom (não-browser)."""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from antibot import SITE, get, solve_challenge  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

html = get(f"{SITE}/wp-sitemap.xml")
cookie = solve_challenge(html)
print("cookie fresco:", cookie[:20])

user = os.getenv("WP_USER")
pw = os.getenv("WP_APP_PASSWORD")
cred = base64.b64encode(f"{user}:{pw}".encode()).decode()

# pega o conteúdo atual (inofensivo)
req = urllib.request.Request(
    f"{SITE}/wp-json/wp/v2/posts/30?_fields=slug,content",
    headers={"Cookie": f"__test={cookie}", "User-Agent": "Mozilla/5.0"},
)
with urllib.request.urlopen(req, timeout=30) as r:
    post = json.loads(r.read().decode())

payload = json.dumps({"content": post["content"]["rendered"]}).encode()
for ua in ("blog-dolar-seo/1.0", "Mozilla/5.0"):
    req = urllib.request.Request(
        f"{SITE}/wp-json/wp/v2/posts/30",
        data=payload,
        headers={
            "Authorization": f"Basic {cred}",
            "Content-Type": "application/json",
            "Cookie": f"__test={cookie}",
            "User-Agent": ua,
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            corpo = r.read().decode(errors="replace")
            print(f"UA={ua!r:22} → status {r.status} | challenge: {'toNumbers' in corpo[:200]} | json: {corpo.strip().startswith('{')}")
    except urllib.error.HTTPError as e:
        print(f"UA={ua!r:22} → HTTPError {e.code}")
