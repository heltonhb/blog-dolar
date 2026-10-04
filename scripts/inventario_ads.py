#!/usr/bin/env python3
"""Inventário dos scripts de anúncio no site — o que o Safe Browsing vê.

Busca as páginas renderizadas, lista TODOS os scripts externos e
classifica os de anúncio (formato do Adsterra) para diagnóstico.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from antibot import get_pagina  # noqa: E402

SITE = "https://techtips.dpdns.org"

# scripts Adsterra conhecidos (do header.php + plugin de banner)
ADSTERRA_IDS = {
    "pl31408097": "head script #1",
    "pl31408098": "head script #2",
    "pl31408157": "banner in-content",
}


def classificar(src: str) -> str:
    if "profitableratecpmnetwork" in src or any(p in src for p in ADSTERRA_IDS):
        return "ANÚNCIO (Adsterra)"
    if "aes.js" in src:
        return "anti-bot InfinityFree"
    return "outro"


for caminho in ("/", "/2026/09/19/how-to-learn-git-version-control/"):
    html = get_pagina(f"{SITE}{caminho}")
    scripts = re.findall(r"<script[^>]*src=[\"']([^\"']+)[\"']", html)
    print(f"\n══ {caminho} — {len(scripts)} scripts externos ══")
    for s in scripts:
        marca = classificar(s)
        pid = next((k for k in ADSTERRA_IDS if k in s), "")
        print(f"  [{marca}] {ADSTERRA_IDS.get(pid, '') + ' — ' if pid else ''}{s[:90]}")
