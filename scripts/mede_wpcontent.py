#!/usr/bin/env python3
"""Mede wp-content do site (pasta a pasta, raso — evita o loop lento)."""
import os
from pathlib import Path

import ftplib
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=30)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))


def tam(p: str):
    try:
        return ftp.size(p)
    except ftplib.error_perm:
        return None


def listar(p: str) -> list[str]:
    try:
        return [e for e in ftp.nlst(p) if e.rstrip("/").split("/")[-1] not in (".", "..")]
    except ftplib.error_perm:
        return []


# níveis: wp-content → subpastas → (mais um nível) → arquivos
totais = {"arq": 0, "bytes": 0, "pastas": 0}


def desce(caminho: str, nivel: int = 0):
    for e in listar(caminho):
        t = tam(e)
        if t is not None:
            totais["arq"] += 1
            totais["bytes"] += t
        else:
            totais["pastas"] += 1
            if nivel < 3:
                desce(e, nivel + 1)


for sub in ("plugins", "themes", "uploads", "mu-plugins"):
    antes = (totais["arq"], totais["bytes"])
    desce(f"htdocs/wp-content/{sub}")
    print(f"  {sub:<12} {(totais['arq']-antes[0]):>4} arq  {(totais['bytes']-antes[1])/1024:>9.1f} KB")

# arquivos soltos
for e in listar("htdocs/wp-content"):
    t = tam(e)
    if t is not None:
        totais["arq"] += 1
        totais["bytes"] += t

print(f"\nwp-content (sem cache): {totais['arq']} arquivos, {totais['bytes']/1024/1024:.2f} MB")
ftp.quit()
