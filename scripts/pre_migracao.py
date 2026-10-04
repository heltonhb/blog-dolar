#!/usr/bin/env python3
"""Pré-migração: o que techtips.dpdns.org já serve?

Verifica: DNS resolvendo, HTTP respondendo, se cai no mesmo WordPress
(anti-bot, homepage, um post) — antes de trocar qualquer URL.
"""
import re
import socket
import sys
import urllib.request

NOVO = "techtips.dpdns.org"
VELHO = "tech-tips.ct.ws"

print("── 1. DNS ──")
try:
    ips = socket.getaddrinfo(NOVO, None)
    print(f"✅ {NOVO} resolve → {sorted({i[4][0] for i in ips})}")
except socket.gaierror as e:
    print(f"❌ DNS não resolve: {e}")
    sys.exit(1)

print("\n── 2. HTTP ──")
req = urllib.request.Request(f"https://{NOVO}/", headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode(errors="replace")
        print(f"HTTP {r.status} | challenge: {'toNumbers' in html[:400]}")
        title = re.search(r"<title>([^<]*)</title>", html)
        print(f"title: {title.group(1)[:60] if title else '?'}")
        print(f"GA4 tag: {'G-G01J573W6J' in html}")
        print(f"é o mesmo WP (tem wp-content): {'wp-content' in html}")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code} — {e.read().decode(errors='replace')[:150]}")
except Exception as e:  # noqa: BLE001
    print(f"❌ {type(e).__name__}: {e}")
