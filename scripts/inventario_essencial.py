#!/usr/bin/env python3
"""Mede SÓ o que é insubstituível em htdocs (wp-content, wp-config, uploads)."""
import os
from pathlib import Path

import ftplib
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=30)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))

ESSENCIAL = ["wp-content", "wp-config.php", ".htaccess"]
total = {"arq": 0, "bytes": 0}


def conta(caminho):
    try:
        entradas = ftp.nlst(caminho)
    except ftplib.error_perm:
        return
    for e in entradas:
        nome = e.rstrip("/").split("/")[-1]
        if nome in (".", ".."):
            continue
        try:
            tam = ftp.size(e)
            if tam is not None:
                total["arq"] += 1
                total["bytes"] += tam
        except ftplib.error_perm:
            conta(e)


for alvo in ESSENCIAL:
    caminho = f"htdocs/{alvo}"
    try:
        ftp.size(caminho)
        total["arq"] += 1
        total["bytes"] += ftp.size(caminho)
        print(f"  arquivo: {caminho}")
        continue
    except ftplib.error_perm:
        pass
    antes = (total["arq"], total["bytes"])
    conta(caminho)
    n = total["arq"] - antes[0]
    mb = (total["bytes"] - antes[1]) / 1024 / 1024
    print(f"  pasta : {caminho} — {n} arquivos, {mb:.2f} MB")

print(f"\nTOTAL: {total['arq']} arquivos, {total['bytes']/1024/1024:.2f} MB")
ftp.quit()
