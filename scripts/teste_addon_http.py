#!/usr/bin/env python3
"""Teste do addon via HTTP (SSL ainda emitindo) + HTTPS com contexto tolerante."""
import re
import ssl
import urllib.request

NOVO = "techtips.dpdns.org"

# 1. HTTP puro
try:
    req = urllib.request.Request(f"http://{NOVO}/", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode(errors="replace")
        title = re.search(r"<title>([^<]*)</title>", html)
        print(f"HTTP: {r.status} | challenge: {'toNumbers' in html[:400]} | title: {title.group(1)[:50] if title else '?'}")
        print(f"WP servido (wp-content): {'wp-content' in html} | GA4: {'G-G01J573W6J' in html}")
except Exception as e:  # noqa: BLE001
    print(f"HTTP falhou: {type(e).__name__}: {e}")

# 2. HTTPS tolerante (só p/ ver o que o cert self-signed entrega agora)
try:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(f"https://{NOVO}/", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        html = r.read().decode(errors="replace")
        title = re.search(r"<title>([^<]*)</title>", html)
        print(f"HTTPS: {r.status} | title: {title.group(1)[:50] if title else '?'}")
except Exception as e:  # noqa: BLE001
    print(f"HTTPS (tolerante) falhou: {type(e).__name__}: {e}")
