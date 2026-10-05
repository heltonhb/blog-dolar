#!/usr/bin/env python3
"""Deploy do mu-plugin tech-tips-ga4-seo.php no site VIVO, com rollback automático.

O site techtips.dpdns.org é um addon domain da InfinityFree: a raiz dele no FTP
é  techtips.dpdns.org/htdocs/  — e NÃO  htdocs/  (que é o site principal da
conta). Deploys anteriores foram para htdocs/ e por isso nunca apareceram no ar.

Fluxo:
  1. baixa o remoto atual → cache/muplugin_backups/<timestamp>.php
  2. envia o local
  3. busca uma página do site e confere marcadores esperados no <head>
  4. se a página quebrou (erro PHP = página sem os marcadores), restaura o backup

Uso:
    python3 scripts/deploy_muplugin.py            # deploy + verificação
    python3 scripts/deploy_muplugin.py --check    # só compara local x remoto e o HTML vivo
"""
import ftplib
import io
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
load_dotenv(ROOT / ".env")

from antibot import SITE, get_pagina  # noqa: E402

LOCAL = ROOT / "scripts" / "tech-tips-ga4-seo.php"
REMOTE = "techtips.dpdns.org/htdocs/wp-content/mu-plugins/tech-tips-ga4-seo.php"
BACKUPS = ROOT / "cache" / "muplugin_backups"
PROBE_URL = f"{SITE}/best-budget-laptops-for-students-2026/"
# Marcadores que o plugin local emite no <head>; todos devem aparecer após o deploy.
MARKERS = (
    "GA4 via mu-plugin",
    "SEO meta via mu-plugin",
    "adsbygoogle.js?client=ca-pub-6258036451330976",
    'name="google-adsense-account"',
    'id="tech-tips-affiliate-css"',
    'name="p:domain_verify"',
)


def _ftp() -> ftplib.FTP:
    ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=30)
    ftp.login(os.environ["FTP_USER"], os.environ["FTP_PASS"])
    return ftp


def _baixar(ftp: ftplib.FTP) -> bytes:
    buf: list[bytes] = []
    ftp.retrbinary(f"RETR {REMOTE}", buf.append)
    return b"".join(buf)


def _verificar_html(tentativas: int = 4) -> list[str]:
    """Marcadores ausentes na página viva ([] = tudo certo)."""
    faltando = list(MARKERS)
    for i in range(tentativas):
        try:
            # cache-buster: o WP Super Cache/CDN pode servir HTML antigo
            pagina = get_pagina(f"{PROBE_URL}?nocache={int(time.time())}")
            faltando = [m for m in MARKERS if m not in pagina]
            if not faltando:
                return []
        except Exception as e:  # noqa: BLE001
            print(f"   tentativa {i + 1}: erro ao buscar página: {e}")
        time.sleep(5)
    return faltando


def main() -> int:
    local = LOCAL.read_bytes()
    with _ftp() as ftp:
        remoto = _baixar(ftp)
        print(f"local={len(local)} bytes  remoto={len(remoto)} bytes  ({REMOTE})")

        if "--check" in sys.argv:
            print("LOCAL == REMOTO" if local == remoto else "⚠️ remoto difere do local")
            faltando = _verificar_html(1)
            print("HTML vivo OK" if not faltando else f"HTML vivo sem: {faltando}")
            return 0 if local == remoto and not faltando else 1

        if local == remoto:
            print("remoto já está atualizado")
        else:
            BACKUPS.mkdir(parents=True, exist_ok=True)
            bak = BACKUPS / f"tech-tips-ga4-seo-{time.strftime('%Y%m%d-%H%M%S')}.php"
            bak.write_bytes(remoto)
            print(f"backup do remoto: {bak.relative_to(ROOT)}")
            ftp.storbinary(f"STOR {REMOTE}", io.BytesIO(local))
            print("✅ enviado mu-plugin")

        pin_html = ROOT / "pinterest-7c193.html"
        if pin_html.exists():
            remote_pin_html = "techtips.dpdns.org/htdocs/pinterest-7c193.html"
            ftp.storbinary(f"STOR {remote_pin_html}", io.BytesIO(pin_html.read_bytes()))
            print(f"✅ enviado arquivo de verificação Pinterest: {remote_pin_html}")

    faltando = _verificar_html()
    if not faltando:
        print("✅ página viva contém todos os marcadores")
        return 0

    print(f"❌ página viva sem: {faltando}")
    if local != remoto:
        print("↩️  restaurando versão anterior…")
        with _ftp() as ftp:
            ftp.storbinary(f"STOR {REMOTE}", io.BytesIO(remoto))
        print("   restaurado. Verifique o erro antes de tentar de novo.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
