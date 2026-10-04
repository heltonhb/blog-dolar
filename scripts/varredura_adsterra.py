#!/usr/bin/env python3
"""Procura TODO arquivo PHP no htdocs que ainda referencie Adsterra.

Varredura completa: header.php pode ter sido regenerado pelo tema,
functions.php de child themes, plugins comuns, wp-config, etc.
"""
import ftplib
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

FTP_HOST = os.environ.get("FTP_HOST", "ftpupload.net")
FTP_USER = os.environ.get("FTP_USER", "")
FTP_PASS = os.environ.get("FTP_PASS", "")


def varrer(ftp, caminho, achados):
    try:
        entradas = ftp.nlst(caminho)
    except ftplib.error_perm:
        return
    for e in entradas:
        if e.endswith("/"):
            e = e[:-1]
        nome = e.split("/")[-1]
        try:
            # tenta como diretório primeiro
            sub = ftp.nlst(e)
            if sub and sub != [e]:
                varrer(ftp, e, achados)
                continue
        except ftplib.error_perm:
            pass
        if not nome.endswith((".php", ".html", ".js", ".txt")):
            continue
        buf = []
        try:
            ftp.retrbinary(f"RETR {e}", buf.append)
        except ftplib.error_perm:
            continue
        txt = b"".join(buf).decode(errors="replace")
        if "profitablerate" in txt or "pl3140" in txt:
            achados.append(e)
            print(f"❌ ACHOU: {e}")
        elif "adsterra" in txt.lower() and nome != "adsterra-ads.php":
            print(f"⚠️ menção 'adsterra' (comentário?): {e}")


def main():
    ftp = ftplib.FTP(FTP_HOST, timeout=20)
    ftp.login(FTP_USER, FTP_PASS)
    achados = []
    for base in ("htdocs/wp-content/themes", "htdocs/wp-content/plugins",
                 "htdocs/wp-content/mu-plugins"):
        print(f"\n── varrendo {base} ──")
        varrer(ftp, base, achados)
    ftp.quit()
    print(f"\n{'🔴 ' + str(len(achados)) + ' arquivo(s) com script ativo' if achados else '🟢 nenhum script Adsterra em themes/plugins/mu-plugins'}")


if __name__ == "__main__":
    main()
