#!/usr/bin/env python3
"""Deploy privacy-policy.html atualizada e verificar ads.txt no servidor FTP."""

import ftplib
import io
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

FTP_HOST = os.environ.get("FTP_HOST", "ftpupload.net")
FTP_USER = os.environ.get("FTP_USER", "")
FTP_PASS = os.environ.get("FTP_PASS", "")

LOCAL_PRIVACY = Path(__file__).parent.parent / "htdocs" / "privacy-policy.html"
LOCAL_ADS_TXT = Path(__file__).parent.parent / "ads.txt"

REMOTE_PRIVACY = "htdocs/privacy-policy.html"
REMOTE_ADS_TXT = "htdocs/ads.txt"

print("=" * 60)
print("Deploy: Privacy Policy + ads.txt para o servidor")
print("=" * 60)

with ftplib.FTP(FTP_HOST, timeout=30) as ftp:
    ftp.login(FTP_USER, FTP_PASS)
    print(f"✅ Conectado a {FTP_HOST}")

    # --- Deploy privacy-policy.html ---
    if LOCAL_PRIVACY.exists():
        data = LOCAL_PRIVACY.read_bytes()
        ftp.storbinary(f"STOR {REMOTE_PRIVACY}", io.BytesIO(data))
        print(f"✅ Privacy policy enviada ({len(data)} bytes) → {REMOTE_PRIVACY}")
    else:
        print(f"❌ Arquivo local não encontrado: {LOCAL_PRIVACY}")

    # --- Verificar/Deploy ads.txt ---
    # Primeiro verifica se já existe no servidor
    remote_ads_exists = False
    remote_ads_content = ""
    try:
        buf = []
        ftp.retrbinary(f"RETR {REMOTE_ADS_TXT}", buf.append)
        remote_ads_content = b"".join(buf).decode(errors="replace").strip()
        remote_ads_exists = True
        print(f"\n📄 ads.txt remoto existente: '{remote_ads_content}'")
    except ftplib.error_perm:
        print("\n⚠️ ads.txt NÃO encontrado no servidor")

    expected = "google.com, pub-6258036451330976, DIRECT, f08c47fec0942fa0"
    if expected in remote_ads_content:
        print("✅ ads.txt remoto contém a linha do AdSense — OK")
    else:
        # Faz upload do local
        if LOCAL_ADS_TXT.exists():
            data = LOCAL_ADS_TXT.read_bytes()
            ftp.storbinary(f"STOR {REMOTE_ADS_TXT}", io.BytesIO(data))
            print(f"✅ ads.txt enviado ({len(data)} bytes) → {REMOTE_ADS_TXT}")
        else:
            # Cria e envia
            ads_content = expected + "\n"
            ftp.storbinary(f"STOR {REMOTE_ADS_TXT}", io.BytesIO(ads_content.encode()))
            print(f"✅ ads.txt criado e enviado → {REMOTE_ADS_TXT}")

    # --- Verificação final ---
    print("\n" + "=" * 60)
    print("Verificação final dos arquivos no servidor:")
    print("=" * 60)
    for remote_path in [REMOTE_PRIVACY, REMOTE_ADS_TXT]:
        try:
            size = ftp.size(remote_path)
            print(f"  ✅ {remote_path} ({size} bytes)")
        except ftplib.error_perm:
            print(f"  ❌ {remote_path} — não encontrado!")

print("\n🎯 Próximo passo: verificar no navegador:")
print("   https://techtips.dpdns.org/privacy-policy.html")
print("   https://techtips.dpdns.org/ads.txt")
