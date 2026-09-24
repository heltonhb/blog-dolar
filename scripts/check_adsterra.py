#!/usr/bin/env python3
"""Verifica se os scripts Adsterra estão presentes no HTML renderizado."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from antibot import get_pagina  # noqa: E402

URLS = [
    "https://tech-tips.ct.ws/2026/09/19/how-to-learn-git-version-control/",
    "https://tech-tips.ct.ws/",
]


def analisar(html: str, url: str) -> None:
    scripts = re.findall(r"<script[^>]*src=[\"']([^\"']+)[\"']", html)
    adsterra = [s for s in scripts if "profitablerate" in s or "pl314" in s]
    print(f"\n── {url}")
    print(f"   scripts totais: {len(scripts)} | adsterra: {len(adsterra)}")
    for s in adsterra:
        print(f"   ✓ {s[:100]}")
    # banner in-content (invoke.js + container)
    invoke = re.findall(r"container-27e8efa95d52426b90979caf133143b3", html)
    print(f"   banner in-content (container): {len(invoke)}")
    # sanity: title da página
    t = re.search(r"<title>([^<]*)</title>", html)
    print(f"   title: {t.group(1)[:60] if t else '?'}")


if __name__ == "__main__":
    for u in URLS:
        analisar(get_pagina(u), u)
