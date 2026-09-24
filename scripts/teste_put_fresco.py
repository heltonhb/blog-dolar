#!/usr/bin/env python3
"""Testa PUT com cookie de sessão fresca (challenge resolvido na hora)."""
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

# 1) challenge resolvido AGORA
html = get(f"{SITE}/wp-sitemap.xml")
cookie = solve_challenge(html)
print("cookie fresco:", cookie[:16], "…")

user = os.getenv("WP_USER")
pw = os.getenv("WP_APP_PASSWORD")
cred = base64.b64encode(f"{user}:{pw}".encode()).decode()

# 2) PUT com esse cookie — mas com o conteúdo ATUAL do post (inofensivo):
#    busco o post primeiro para não corromper nada
url_get = f"{SITE}/wp-json/wp/v2/posts/30?_fields=slug,content"
req = urllib.request.Request(
    url_get, headers={"Cookie": f"__test={cookie}", "User-Agent": "Mozilla/5.0"}
)
with urllib.request.urlopen(req, timeout=30) as r:
    post = json.loads(r.read().decode())
print("post:", post["slug"], "| tamanho conteúdo:", len(post["content"]["rendered"]))

# 3) PUT devolvendo o MESMO conteúdo
payload = json.dumps({"content": post["content"]["rendered"]}).encode()
req = urllib.request.Request(
    f"{SITE}/wp-json/wp/v2/posts/30",
    data=payload,
    headers={
        "Authorization": f"Basic {cred}",
        "Content-Type": "application/json",
        "Cookie": f"__test={cookie}",
        "User-Agent": "Mozilla/5.0",
    },
    method="PUT",
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        corpo = r.read().decode(errors="replace")
        print("status:", r.status, "| challenge?:", "toNumbers" in corpo[:200], "| json?:", corpo.strip().startswith("{"))
except urllib.error.HTTPError as e:
    print("HTTPError", e.code, e.read().decode()[:200])
