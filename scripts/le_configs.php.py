#!/usr/bin/env python3
"""Lê os wp-configs com regex correta (define('X', 'Y')) + tenta HTTP p/ SSL."""
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

ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=20)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))


def le_config(caminho: str) -> dict:
    buf = []
    ftp.retrbinary(f"RETR {caminho}", buf.append)
    cfg = b"".join(buf).decode(errors="replace")
    out = {}
    for campo in ("DB_NAME", "DB_USER", "DB_HOST"):
        m = re.search(rf"define\(\s*'{campo}'\s*,\s*'([^']+)'", cfg)
        out[campo] = m.group(1) if m else "?"
    m = re.search(r"\$table_prefix\s*=\s*'([^']+)'", cfg)
    out["prefix"] = m.group(1) if m else "?"
    return out


novo = le_config("techtips.dpdns.org/htdocs/wp-config.php")
velho = le_config("htdocs/wp-config.php")
ftp.quit()

print("wp-config NOVO (addon):")
for k, v in novo.items():
    print(f"   {k}: {v}")
print("\nwp-config ANTIGO (htdocs):")
for k, v in velho.items():
    print(f"   {k}: {v}")

print(f"\nmesmo banco? {'✅ SIM' if novo['DB_NAME'] == velho['DB_NAME'] else '❌ NÃO (vou trocar)'}")
print(f"prefixo novo: {novo['prefix']} | antigo: {velho['prefix']}")

# HTTP (SSL ainda self-signed) — site novo responde?
antibot.SITE = f"http://{NOVO}"
try:
    html = antibot.get(f"http://{NOVO}/")
    if "toNumbers" in html:
        cookie = antibot.solve_challenge(html)
        html = antibot.get(f"http://{NOVO}/", cookie=cookie)
    title = re.search(r"<title>([^<]*)</title>", html)
    print(f"\nsite via HTTP: {title.group(1)[:60] if title else 'sem title'} | "
          f"{'WP instalado' if 'wp-content' in html else '???'}")
except Exception as e:  # noqa: BLE001
    print(f"\nsite via HTTP: ❌ {type(e).__name__}: {e}")
