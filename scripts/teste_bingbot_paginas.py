#!/usr/bin/env python3
"""O que o Bingbot recebe ao buscar uma PÁGINA de post (sem cookie)?"""
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

SITE = "https://tech-tips.ct.ws"

UAS = {
    "Googlebot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Bingbot": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
}

URLS = [
    "/2026/09/19/how-to-learn-git-version-control/",
    "/",
    "/privacy-policy/",
]

for nome, ua in UAS.items():
    for caminho in URLS:
        req = urllib.request.Request(f"{SITE}{caminho}", headers={"User-Agent": ua})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                corpo = r.read().decode(errors="replace")
                challenge = "toNumbers" in corpo[:400]
                tem_conteudo = "Related Articles" in corpo or "Tech Tips" in corpo[:2000]
                print(f"{nome:<10} {caminho:<45} HTTP {r.status} | challenge: "
                      f"{'SIM' if challenge else 'NÃO'} | conteúdo real: {'✓' if tem_conteudo and not challenge else '—'}")
        except Exception as e:  # noqa: BLE001
            print(f"{nome:<10} {caminho:<45} ERRO: {type(e).__name__}: {e}")
