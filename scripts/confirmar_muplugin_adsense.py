#!/usr/bin/env python3
"""Confirma que o mu-plugin remoto tech-tips-ga4-seo.php
contém o script global do AdSense e que o local bate com o remoto."""

import io
import os
import sys
import ftplib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

FTP_HOST = os.environ.get("FTP_HOST", "ftpupload.net")
FTP_USER = os.environ.get("FTP_USER", "")
FTP_PASS = os.environ.get("FTP_PASS", "")
# techtips.dpdns.org é addon domain: a raiz dele é techtips.dpdns.org/htdocs/
# (htdocs/ sozinho é o site principal da conta e não é servido neste domínio).
REMOTE = "techtips.dpdns.org/htdocs/wp-content/mu-plugins/tech-tips-ga4-seo.php"
LOCAL = Path(__file__).parent / "tech-tips-ga4-seo.php"

if not LOCAL.exists():
    sys.exit(f"❌ arquivo local não encontrado: {LOCAL}")

LOCAL_BYTES = LOCAL.read_bytes()
LOCAL_TXT = LOCAL_BYTES.decode(errors="replace")

print(f"arquivo local: {LOCAL} ({len(LOCAL_BYTES)} bytes)")

with ftplib.FTP(FTP_HOST, timeout=30) as ftp:
    ftp.login(FTP_USER, FTP_PASS)
    try:
        tam_remoto = ftp.size(REMOTE)
    except ftplib.error_perm as e:
        print(f"❌ remoto não acessível ({REMOTE}): {e}")
        sys.exit(1)

    buf = []
    ftp.retrbinary(f"RETR {REMOTE}", buf.append)
    REMOTO_BYTES = b"".join(buf)
    REMOTO_TXT = REMOTO_BYTES.decode(errors="replace")

    print(f"remoto ({REMOTE}): {len(REMOTO_BYTES)} bytes")

    adsense_meta = "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6258036451330976"
    presente_local = adsense_meta in LOCAL_TXT
    presente_remoto = adsense_meta in REMOTO_TXT

    print(f"script AdSense no LOCAL : {'✅' if presente_local else '❌'}")
    print(f"script AdSense no REMOTO: {'✅' if presente_remoto else '❌'}")

    if len(LOCAL_BYTES) != len(REMOTO_BYTES):
        print("⚠️ tamanho local != remoto — arquivo remoto difere do local")
        print(f"   local={len(LOCAL_BYTES)} remoto={len(REMOTO_BYTES)}")
        diff_nome = REMOTE.replace("/", "_").replace(".", "_") + "_diferente.php"
        Path(diff_nome).write_bytes(REMOTO_BYTES)
        print(f"   remoto salvo em: {diff_nome} (para análise manual se quiser)")
        sys.exit(2)

    if LOCAL_BYTES != REMOTO_BYTES:
        print("⚠️ conteúdo difere (mesmo tamanho) — remoto não está atualizado")
        diff_nome = REMOTE.replace("/", "_").replace(".", "_") + "_diferente.php"
        Path(diff_nome).write_bytes(REMOTO_BYTES)
        print(f"   remoto salvo em: {diff_nome}")
        sys.exit(3)

    print("✅ LOCAL == REMOTO (idênticos)")

print("\nResumo:")
if presente_local and presente_remoto:
    print("  script AdSense presente no mu-plugin — OK")
else:
    print("  ⚠️ script AdSense NÃO presente onde deveria estar")
