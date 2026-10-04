#!/usr/bin/env python3
"""Addon via HTTP puro (SSL ainda emitindo): o que está servido?"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import antibot  # noqa: E402

NOVO = "techtips.dpdns.org"
# tudo por http até o SSL da InfinityFree emitir
antibot.SITE = f"http://{NOVO}"


def get_http(url: str) -> str:
    u = url.replace("https://", "http://")
    html = antibot.get(u)
    if "toNumbers" in html:
        cookie = antibot.solve_challenge(html)
        html = antibot.get(u, cookie=cookie)
    return html


html = get_http(f"http://{NOVO}/")
title = re.search(r"<title>([^<]*)</title>", html)
print(f"tamanho: {len(html)} | title: {title.group(1)[:60] if title else '(sem title)'}")
print(f"WP (wp-content): {'wp-content' in html}")
print(f"GA4: {'G-G01J573W6J' in html}")

m = re.search(r'rel="canonical" href="([^"]+)"', html)
print(f"canonical: {m.group(1) if m else '(sem canonical)'}")

print("\n── trecho do body ──")
i = html.find("<body")
print(html[i : i + 600] if i >= 0 else html[:600])
