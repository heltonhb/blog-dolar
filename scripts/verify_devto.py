#!/usr/bin/env python3
"""Verifica artigos publicados no Dev.to: status, tags, canonical e CTA."""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

sys_path = Path(__file__).parent
import sys  # noqa: E402

sys.path.insert(0, str(sys_path))

load_dotenv(Path(__file__).parent.parent / ".env")

key = os.getenv("DEVTO_API_KEY", "")
H = {
    "api-key": key,
    "Accept": "application/json",
    "User-Agent": "blog-dolar-publisher/1.0 (verification)",
}


def _get(url: str) -> tuple[int, Any]:
    req = urllib.request.Request(url, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:200]


status, me = _get("https://dev.to/api/articles/me/all?per_page=50")
if status != 200 or not isinstance(me, list):
    raise SystemExit(f"falha: {me}")

ok_cta = 0
for a in me:
    if not isinstance(a, dict):
        continue
    s, full = _get(f"https://dev.to/api/articles/{a['id']}")
    if not isinstance(full, dict):
        print(f"⚪ {a['title'][:50]}: detalhes indisponíveis ({s})")
        continue
    tags = full.get("tags", [])
    body = full.get("body_markdown", "")
    cta = "Originally published on [Tech Tips]" in body
    ok_cta += cta
    simb = "🟢" if a["published"] and cta else "⚠️"
    print(f"{simb} {a['title'][:52]:<52} | tags: {len(tags)} | CTA: {'✓' if cta else 'FALTA'}")

print(f"\n{ok_cta}/{len(me)} artigos publicados com CTA ativo")
