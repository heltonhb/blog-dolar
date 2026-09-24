#!/usr/bin/env python3
"""Sobe a key do IndexNow para /.well-known/ e limpa o cache do WP Super Cache.

IndexNow exige que https://host/.well-known/<key>.txt responda com a key.
Sem a limpeza do cache, as mudanças (links internos) não aparecem no site.
"""
import ftplib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from indexnow_submit import KEY_FILE, obter_key  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

FTP_HOST = os.environ.get("FTP_HOST", "ftpupload.net")
FTP_USER = os.environ.get("FTP_USER", "")
FTP_PASS = os.environ.get("FTP_PASS", "")


def subir_key() -> str:
    key = obter_key()
    ftp = ftplib.FTP(FTP_HOST, timeout=15)
    ftp.login(FTP_USER, FTP_PASS)

    # garante htdocs/.well-known/
    try:
        ftp.cwd("htdocs")
    except ftplib.error_perm:
        pass
    try:
        ftp.mkd(".well-known")
    except ftplib.error_perm:
        pass  # já existe
    ftp.cwd(".well-known")

    # arquivo <key>.txt com o conteúdo = key
    dados = key.encode()
    import io

    ftp.storbinary(f"STOR {key}.txt", io.BytesIO(dados))
    print(f"✅ key publicada: htdocs/.well-known/{key}.txt")
    ftp.quit()
    return key


def limpar_cache() -> int:
    """Apaga wp-content/cache/page_enhanced/* (WP Super Cache)."""
    ftp = ftplib.FTP(FTP_HOST, timeout=15)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.cwd("htdocs/wp-content/cache/page_enhanced")

    removidos = 0

    def _apagar_dir(path: str) -> None:
        nonlocal removidos
        try:
            entradas = ftp.nlst(path)
        except ftplib.error_perm:
            return
        for e in entradas:
            if e.endswith("/") or "/" not in e.rsplit("/", 1)[-1]:
                # entrada de diretório (subpasta do domínio)
                try:
                    _apagar_dir(e)
                except ftplib.error_perm:
                    pass
            try:
                ftp.delete(e)
                removidos += 1
            except ftplib.error_perm:
                try:
                    ftp.rmd(e)
                    removidos += 1
                except ftplib.error_perm:
                    pass

    _apagar_dir(".")
    ftp.quit()
    return removidos


if __name__ == "__main__":
    acao = sys.argv[1] if len(sys.argv) > 1 else "tudo"
    if acao in ("key", "tudo"):
        subir_key()
    if acao in ("cache", "tudo"):
        n = limpar_cache()
        print(f"🧹 {n} arquivo(s) de cache removido(s)")
