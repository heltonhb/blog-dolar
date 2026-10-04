#!/usr/bin/env python3
"""Diagnóstico do 500: estrutura de pastas + caminho do wp-blog-header."""
import os
import sys
from pathlib import Path

import ftplib
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=20)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))

print("── raiz do addon ──")
for e in ftp.nlst("techtips.dpdns.org"):
    print("  ", e)

print("\n── wp-blog-header existe em htdocs? ──")
try:
    buf = []
    ftp.retrbinary("RETR htdocs/wp-blog-header.php", buf.append)
    txt = b"".join(buf).decode(errors="replace")
    print(f"✅ existe ({len(txt)} chars) — começa com: {txt[:80]!r}")
except Exception as e:  # noqa: BLE001
    print(f"❌ {e}")

print("\n── index.php atual do addon ──")
buf = []
try:
    ftp.retrbinary("RETR techtips.dpdns.org/htdocs/index.php", buf.append)
    print(b"".join(buf).decode(errors="replace"))
except Exception as e:  # noqa: BLE001
    print(f"❌ {e}")

ftp.quit()
