#!/usr/bin/env python3
"""Pré-voo Bing Webmaster Tools: o que o Bingbot vai encontrar.

Verifica: robots.txt (com UA de bot), sitemap, arquivo de verificação
do Google Search Console e resposta do anti-bot a UAs de crawler.
"""
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from antibot import get, solve_challenge  # noqa: E402

SITE = "https://tech-tips.ct.ws"

UAS = {
    "sem UA (Python)": "Python-urllib/3.12",
    "Mozilla/5.0": "Mozilla/5.0",
    "Googlebot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Bingbot": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
}


def testar_ua(nome: str, ua: str, url: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            corpo = r.read().decode(errors="replace")
            bloqueado = "toNumbers" in corpo[:300]
            print(f"  {nome:<18} → HTTP {r.status} | challenge: {'SIM' if bloqueado else 'NÃO'}")
    except Exception as e:  # noqa: BLE001
        print(f"  {nome:<18} → ERRO: {e}")


print("── 1. robots.txt sob a visão de cada User-Agent ──")
for nome, ua in UAS.items():
    testar_ua(nome, ua, f"{SITE}/robots.txt")

print("\n── 2. sitemap (wp-sitemap.xml) com Bingbot ──")
testar_ua("Bingbot", UAS["Bingbot"], f"{SITE}/wp-sitemap.xml")

print("\n── 3. conteúdo do robots.txt (via cookie) ──")
from antibot import get_pagina  # noqa: E402

robots = get_pagina(f"{SITE}/robots.txt")
print(robots[:400])

print("\n── 4. arquivo de verificação do Google (GSC) no ar? ──")
import re  # noqa: E402

m = re.search(r"google([0-9a-f]+)\.html", open(Path(__file__).parent.parent / "google36841e3dc65b42a5.html").read() or "google36841e3dc65b42a5")
arq = "google36841e3dc65b42a5.html"
try:
    corpo = get_pagina(f"{SITE}/{arq}")
    print(f"  {arq} → {'✅ no ar' if 'google-site-verification' in corpo else f'⚠️ conteúdo inesperado: {corpo[:80]!r}'}")
except Exception as e:  # noqa: BLE001
    print(f"  {arq} → ❌ {e}")
