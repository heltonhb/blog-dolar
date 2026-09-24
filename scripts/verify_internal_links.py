#!/usr/bin/env python3
"""Verifica se o bloco Related Articles está visível nos posts renderizados."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from antibot import get_pagina  # noqa: E402
from fetch_urls import fetch_post_urls  # noqa: E402


def main():
    urls = fetch_post_urls()
    ok = 0
    for u in urls:
        html = get_pagina(u)
        tem_bloco = "Related Articles" in html
        n_links = len(re.findall(r'href="https://tech-tips\.ct\.ws/2026', html)) - 1
        ok += tem_bloco
        simb = "🟢" if tem_bloco else "⚪"
        print(f"{simb} {u.split('/')[-2]:<55} bloco: {'✓' if tem_bloco else '—'}")
    print(f"\n{ok}/{len(urls)} posts com bloco de links internos no ar")


if __name__ == "__main__":
    main()
