#!/usr/bin/env python3
"""Captura o corpo do erro 500 (a mensagem real do PHP)."""
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import antibot  # noqa: E402

NOVO = "techtips.dpdns.org"
antibot.SITE = f"http://{NOVO}"

url = f"http://{NOVO}/"
html = antibot.get(url)
cookie = antibot.solve_challenge(html) if "toNumbers" in html else ""

req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                           **({"Cookie": f"__test={cookie}"} if cookie else {})})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("OK agora?", r.status)
        print(r.read().decode(errors="replace")[:300])
except urllib.error.HTTPError as e:
    corpo = e.read().decode(errors="replace")
    print(f"HTTP {e.code}")
    print("── corpo do erro ──")
    print(corpo[:1000])
