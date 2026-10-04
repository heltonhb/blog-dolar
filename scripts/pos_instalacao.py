#!/usr/bin/env python3
"""Pós-instalação: o WP novo está no ar? Que banco/config ele tem?

1. HTTP no novo domínio (via anti-bot)
2. wp-config.php do addon (banco/prefixo que o Softaculous criou)
3. wp-config.php do site antigo (para comparar credenciais)
"""
import io
import os
import re
import sys
import urllib.request
from pathlib import Path

import ftplib
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
import antibot  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

NOVO = "techtips.dpdns.org"

# ── 1. site responde? ──────────────────────────────────────────────────────
antibot.SITE = f"https://{NOVO}"
try:
    html = antibot.get(f"https://{NOVO}/")
    if "toNumbers" in html:
        cookie = antibot.solve_challenge(html)
        html = antibot.get(f"https://{NOVO}/", cookie=cookie)
    title = re.search(r"<title>([^<]*)</title>", html)
    print(f"1. site: {'✅ no ar' if '<html' in html else '❌'} | title: {title.group(1)[:50] if title else '?'}")
    print(f"   challenge atravessado | tamanho: {len(html)} chars")
except Exception as e:  # noqa: BLE001
    print(f"1. site: ❌ {type(e).__name__}: {e}")

# ── 2. wp-config do addon (novo) ───────────────────────────────────────────
ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=20)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))

buf = []
try:
    ftp.retrbinary("RETR techtips.dpdns.org/htdocs/wp-config.php", buf.append)
    cfg = b"".join(buf).decode(errors="replace")
    print("\n2. wp-config NOVO (addon):")
    for campo in ("DB_NAME", "DB_USER", "DB_HOST", "table_prefix"):
        m = re.search(rf"['\"]?{campo}['\"]?\s*[,]?\s*=\s*['\"]([^'\"]+)", cfg)
        print(f"   {campo}: {m.group(1) if m else '?'}")
except Exception as e:  # noqa: BLE001
    print(f"\n2. wp-config NOVO: ❌ {e}")

# ── 3. wp-config do site antigo ─────────────────────────────────────────────
buf = []
try:
    ftp.retrbinary("RETR htdocs/wp-config.php", buf.append)
    cfg = b"".join(buf).decode(errors="replace")
    print("\n3. wp-config ANTIGO (htdocs):")
    for campo in ("DB_NAME", "DB_USER", "DB_HOST", "table_prefix"):
        m = re.search(rf"['\"]?{campo}['\"]?\s*[,]?\s*=\s*['\"]([^'\"]+)", cfg)
        print(f"   {campo}: {m.group(1) if m else '?'}")
except Exception as e:  # noqa: BLE001
    print(f"\n3. wp-config ANTIGO: ❌ {e}")

# ── 4. conteúdo da pasta do addon ───────────────────────────────────────────
print("\n4. addon/htdocs:")
for e in sorted(ftp.nlst("techtips.dpdns.org/htdocs"))[:25]:
    nome = e.rstrip("/").split("/")[-1]
    if nome not in (".", ".."):
        print("  ", nome)

ftp.quit()
