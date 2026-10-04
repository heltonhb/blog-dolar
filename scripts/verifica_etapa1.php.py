#!/usr/bin/env python3
"""Etapa 1 verificada: o WP do addon carrega o conteúdo do banco antigo?"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import antibot  # noqa: E402

NOVO = "techtips.dpdns.org"
antibot.SITE = f"http://{NOVO}"


def get_http(url: str) -> str:
    html = antibot.get(url)
    if "toNumbers" in html:
        cookie = antibot.solve_challenge(html)
        html = antibot.get(url, cookie=cookie)
    return html


html = get_http(f"http://{NOVO}/")
title = re.search(r"<title>([^<]*)</title>", html)
print(f"title: {title.group(1)[:60] if title else '?'}")

# posts visíveis na home?
links = re.findall(r'href="(https?://[^"]*techtips\.dpdns\.org/2026/[^"]+)"', html)
links += re.findall(r'href="(https?://[^"]*tech-tips\.ct\.ws/2026/[^"]+)"', html)
print(f"links de posts na home: {len(links)}")
for l in links[:5]:
    print("  ", l)

# um post direto
post = get_http(f"http://{NOVO}/2026/09/19/how-to-learn-git-version-control/")
t2 = re.search(r"<title>([^<]*)</title>", post)
print(f"\npost git: {t2.group(1)[:60] if t2 else 'ERRO/404'}")
print(f"GA4: {'G-G01J573W6J' in post} | Related: {'Related Articles' in post}")
