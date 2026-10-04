#!/usr/bin/env python3
"""Inventário: quantos arquivos tem em htdocs (para o plano C de cópia)."""
import os
from pathlib import Path

import ftplib
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=30)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))

total = {"arq": 0, "dirs": 0, "bytes": 0}
por_tipo = {}


def conta(caminho="."):
    try:
        entradas = ftp.nlst(caminho)
    except ftplib.error_perm:
        return
    for e in entradas:
        nome = e.rstrip("/").split("/")[-1]
        if nome in (".", ".."):
            continue
        try:
            ftp.size(e)
            total["arq"] += 1
            total["bytes"] += ftp.size(e) or 0
            ext = nome.rsplit(".", 1)[-1] if "." in nome else "(sem ext)"
            por_tipo[ext] = por_tipo.get(ext, 0) + 1
        except ftplib.error_perm:
            total["dirs"] += 1
            if total["dirs"] < 400:  # limite de profundidade/segurança
                conta(e)


conta("htdocs")
print(f"arquivos: {total['arq']} | diretórios: {total['dirs']} | "
      f"tamanho: {total['bytes']/1024/1024:.1f} MB")
print("por extensão (top 12):")
for ext, n in sorted(por_tipo.items(), key=lambda x: -x[1])[:12]:
    print(f"  .{ext}: {n}")
ftp.quit()
