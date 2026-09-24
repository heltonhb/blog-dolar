#!/usr/bin/env python3
"""Limpa o cache do WP Super Cache via FTP (page_enhanced), 2 níveis."""
import ftplib
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

FTP_HOST = os.environ.get("FTP_HOST", "ftpupload.net")
FTP_USER = os.environ.get("FTP_USER", "")
FTP_PASS = os.environ.get("FTP_PASS", "")


def limpar_cache() -> int:
    ftp = ftplib.FTP(FTP_HOST, timeout=20)
    ftp.login(FTP_USER, FTP_PASS)
    removidos = 0

    try:
        ftp.cwd("htdocs/wp-content/cache/page_enhanced")
    except ftplib.error_perm:
        print("ℹ️ page_enhanced inexistente — cache já limpo")
        ftp.quit()
        return 0

    # nível 1: domínios
    for dominio in ftp.nlst("."):
        try:
            subs = ftp.nlst(dominio)
        except ftplib.error_perm:
            subs = []
        # nível 2: caminhos de página (ex.: 2026/09/19/slug/)
        for sub in subs:
            try:
                arquivos = ftp.nlst(sub)
            except ftplib.error_perm:
                arquivos = []
            for a in arquivos:
                try:
                    ftp.delete(a)
                    removidos += 1
                except ftplib.error_perm:
                    pass
            try:
                ftp.rmd(sub)
                removidos += 1
            except ftplib.error_perm:
                pass
        try:
            ftp.rmd(dominio)
            removidos += 1
        except ftplib.error_perm:
            pass

    ftp.quit()
    return removidos


if __name__ == "__main__":
    n = limpar_cache()
    print(f"🧹 {n} entradas removidas de page_enhanced")
