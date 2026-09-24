#!/usr/bin/env python3
"""Verifica e corrige a publicação da key IndexNow (anti-bot no caminho)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from antibot import get_pagina, obter_cookie  # noqa: E402

key = "bcf6a1f7356bdd9c03994d747ba7aa49"
url = f"https://tech-tips.ct.ws/.well-known/{key}.txt"

cookie = obter_cookie()
print(f"cookie: {cookie[:12]}…")
html = get_pagina(url)
print(f"resposta ({len(html)} chars):")
print(html[:200])
ok = html.strip() == key
print(f"\n{'✅' if ok else '❌'} key acessível: {ok}")
