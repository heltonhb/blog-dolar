#!/usr/bin/env python3
"""Diagnóstico do 500 nos posts: .htaccess + temas/plugins da pasta nova."""
import os
from pathlib import Path

import ftplib
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=20)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))


def le(caminho):
    buf = []
    try:
        ftp.retrbinary(f"RETR {caminho}", buf.append)
        return b"".join(buf).decode(errors="replace")
    except Exception as e:  # noqa: BLE001
        return f"(erro: {e})"


print("── .htaccess do addon ──")
print(le("techtips.dpdns.org/htdocs/.htaccess")[:600])

print("\n── temas no addon ──")
for e in ftp.nlst("techtips.dpdns.org/htdocs/wp-content/themes"):
    n = e.rstrip("/").split("/")[-1]
    if n not in (".", ".."):
        print("  ", n)

print("\n── temas no antigo ──")
for e in ftp.nlst("htdocs/wp-content/themes"):
    n = e.rstrip("/").split("/")[-1]
    if n not in (".", ".."):
        print("  ", n)

print("\n── plugins antigo ──")
for e in ftp.nlst("htdocs/wp-content/plugins"):
    n = e.rstrip("/").split("/")[-1]
    if n not in (".", ".."):
        print("  ", n)

print("\n── mu-plugins antigo ──")
for e in ftp.nlst("htdocs/wp-content/mu-plugins"):
    n = e.rstrip("/").split("/")[-1]
    if n not in (".", ".."):
        print("  ", n)

ftp.quit()
