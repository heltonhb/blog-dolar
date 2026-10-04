#!/usr/bin/env python3
"""Localiza e remove TODOS os scripts Adsterra restantes do site.

1) mu-plugins e plugins com banner in-content (FTP: wp-content/mu-plugins/)
2) functions.php do tema (banner via the_content)
3) confere o header.php pós-remoção
"""
import ftplib
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

FTP_HOST = os.environ.get("FTP_HOST", "ftpupload.net")
FTP_USER = os.environ.get("FTP_USER", "")
FTP_PASS = os.environ.get("FTP_PASS", "")


def ftp_nl(ftp, path="."):
    try:
        return ftp.nlst(path)
    except ftplib.error_perm:
        return []


def main():
    ftp = ftplib.FTP(FTP_HOST, timeout=20)
    ftp.login(FTP_USER, FTP_PASS)

    achados = []

    # 1) mu-plugins
    for f in ftp_nl(ftp, "htdocs/wp-content/mu-plugins"):
        nome = f.split("/")[-1]
        if not nome.endswith(".php"):
            continue
        conteudo = []
        try:
            ftp.retrbinary(f"RETR {f}", conteudo.append)
        except ftplib.error_perm:
            continue
        txt = b"".join(conteudo).decode(errors="replace")
        if "profitablerate" in txt or "adsterra" in txt.lower():
            achados.append(("mu-plugin", f))
            ftp.delete(f)
            print(f"🗑️ removido mu-plugin: {nome}")

    # 2) functions.php do tema
    fn = "htdocs/wp-content/themes/astra/functions.php"
    conteudo = []
    try:
        ftp.retrbinary(f"RETR {fn}", conteudo.append)
        txt = b"".join(conteudo).decode(errors="replace")
        if "profitablerate" in txt or "adsterra" in txt.lower():
            print(f"⚠️ functions.php contém adsterra — trecho:")
            for i, linha in enumerate(txt.splitlines()):
                if "profitablerate" in linha or "adsterra" in linha.lower():
                    print(f"   L{i}: {linha.strip()[:100]}")
            achados.append(("functions.php", fn))
        else:
            print("✓ functions.php limpo")
    except ftplib.error_perm:
        print("ℹ️ functions.php não acessível")

    # 3) header.php pós-remoção — confere
    hd = "htdocs/wp-content/themes/astra/header.php"
    conteudo = []
    ftp.retrbinary(f"RETR {hd}", conteudo.append)
    txt = b"".join(conteudo).decode(errors="replace")
    print(f"{'✓' if 'profitablerate' not in txt else '❌ AINDA TEM'} header.php pós-remoção")

    ftp.quit()
    if not achados:
        print("\n✅ nenhum script adsterra fora do header")


if __name__ == "__main__":
    main()
