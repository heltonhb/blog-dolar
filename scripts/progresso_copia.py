#!/usr/bin/env python3
"""Progresso da cópia: quantos arquivos já estão no destino?"""
import os
from pathlib import Path

import ftplib
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=20)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))

# NÃO logar com a mesma sessão do processo em paralelo — só NLST rápido
totais = {}
for base in ("themes/astra", "plugins", "mu-plugins"):
    destino = f"techtips.dpdns.org/htdocs/wp-content/{base}"
    try:
        totais[base] = len([e for e in ftp.nlst(destino)
                            if e.rstrip("/").split("/")[-1] not in (".", "..")])
    except ftplib.error_perm:
        totais[base] = "não existe"
print(totais)

# amostra da astra
try:
    print("\nastra/ raiz:")
    for e in ftp.nlst("techtips.dpdns.org/htdocs/wp-content/themes/astra")[:15]:
        print("  ", e.rstrip("/").split("/")[-1])
except Exception as ex:  # noqa: BLE001
    print("astra:", ex)
ftp.quit()
