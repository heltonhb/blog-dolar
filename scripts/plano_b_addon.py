#!/usr/bin/env python3
"""Plano B da migração: addon em pasta própria carregando o WP de htdocs.

1. Lê o estado atual (pastas do addon)
2. Sobe index.php bootstrap na pasta do addon
3. Verifica o novo domínio servindo o WordPress
"""
import os
import sys
from pathlib import Path

import ftplib
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

FTP_HOST = os.environ.get("FTP_HOST", "ftpupload.net")
FTP_USER = os.environ.get("FTP_USER", "")
FTP_PASS = os.environ.get("FTP_PASS", "")

ADDON_DIR = "techtips.dpdns.org"

# Bootstrap: carrega o WordPress que vive em ../htdocs
INDEX_BOOTSTRAP = """<?php
/**
 * Bootstrap: este addon domain serve o WordPress instalado em /htdocs.
 * Não copie arquivos — apenas aponte para o wp-load.php real.
 */
define('WP_USE_THEMES', true);
require dirname(__DIR__) . '/htdocs/wp-blog-header.php';
"""


def main():
    ftp = ftplib.FTP(FTP_HOST, timeout=20)
    ftp.login(FTP_USER, FTP_PASS)

    # 1. estado atual da home do usuário
    print("── conteúdo da raiz da conta ──")
    entradas = ftp.nlst(".")
    for e in entradas:
        print("  ", e)

    # 2. a pasta do addon existe? o que tem dentro?
    print(f"\n── pasta do addon: {ADDON_DIR} ──")
    try:
        conteudo = ftp.nlst(ADDON_DIR)
        for c in conteudo:
            print("  ", c)
    except ftplib.error_perm:
        print("  (não existe ou vazia — o painel disse que cria na adição)")

    # 3. sobe o bootstrap no public root do addon (techtips.dpdns.org/htdocs)
    import io

    addon_root = f"{ADDON_DIR}/htdocs"
    try:
        ftp.storbinary(f"STOR {addon_root}/index.php", io.BytesIO(INDEX_BOOTSTRAP.encode()))
        print(f"\n✅ index.php bootstrap enviado para {addon_root}/")
    except ftplib.error_perm as e:
        print(f"\n❌ falha ao subir bootstrap: {e}")
        ftp.quit()
        sys.exit(1)

    # 4. confere o que ficou lá
    buf = []
    ftp.retrbinary(f"RETR {addon_root}/index.php", buf.append)
    ok = b"wp-blog-header" in b"".join(buf)
    print(f"{'✅' if ok else '❌'} index.php verificado no FTP")

    ftp.quit()

    print("\nPróximo passo: aguardar propagação e testar https://techtips.dpdns.org/")
    print("(o DNS pode levar alguns minutos para começar a responder)")


if __name__ == "__main__":
    main()
