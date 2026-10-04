#!/usr/bin/env python3
"""Migração Plano G — etapa 5: redirect 301 no htdocs ANTIGO → domínio novo.

⚠️ SÓ RODAR DEPOIS de:
  - etapa 3 (.htaccess do addon com permalinks)
  - etapa 4 (URLs do banco migradas)
  - verificação básica do site novo (home + posts no ar)

O que faz:
  1. Backup local do .htaccess atual do htdocs antigo
  2. Escreve .htaccess novo no htdocs antigo:
     - 301 de TUDO (http e https, www e não-www) → https://techtips.dpdns.org
     - EXCEÇÕES: arquivo de verificação do Google (google*.html) continua
       200 — Search Console da propriedade antiga precisa revalidar
     - robots.txt também continua 200 (declara Sitemap: novo domínio) para
       os crawlers entenderem a mudança de host
"""
import io
import os
from pathlib import Path

import ftplib
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

NOVO = "https://techtips.dpdns.org"

HTACCESS = f"""# Migration: tech-tips.ct.ws → {NOVO} (Plano G, 25/09/2026)
<IfModule mod_rewrite.c>
RewriteEngine On

# Google Search Console verification file stays reachable (200)
RewriteCond %{{REQUEST_URI}} !^/google[0-9a-f]+\\.html$
# robots.txt stays reachable so crawlers see the new sitemap
RewriteCond %{{REQUEST_URI}} !^/robots\\.txt$

# everything else → 301 to the new domain, path preserved
RewriteRule ^(.*)$ {NOVO}/$1 [R=301,L]
</IfModule>
"""

ROBOTS = f"""User-agent: *
Disallow:

Sitemap: {NOVO}/wp-sitemap.xml
"""

ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=30)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))

# 1. backup do .htaccess antigo atual
buf = []
try:
    ftp.retrbinary("RETR htdocs/.htaccess", buf.append)
    Path("scripts/_backup_htaccess_antigo_pre301").write_text(
        b"".join(buf).decode(errors="replace")
    )
    print("✅ backup do .htaccess antigo salvo em scripts/_backup_htaccess_antigo_pre301")
except Exception as e:  # noqa: BLE001
    print(f"(sem .htaccess antigo p/ backup: {e})")

# 2. sobe o .htaccess do redirect
ftp.storbinary("STOR htdocs/.htaccess", io.BytesIO(HTACCESS.encode()))
print("✅ .htaccess 301 instalado no htdocs antigo")

# 3. robots.txt do domínio antigo aponta pro sitemap novo
buf = []
try:
    ftp.retrbinary("RETR htdocs/robots.txt", buf.append)
    Path("scripts/_backup_robots_antigo").write_text(
        b"".join(buf).decode(errors="replace")
    )
    print("✅ backup do robots.txt antigo salvo")
except Exception as e:  # noqa: BLE001
    print(f"(sem robots.txt antigo p/ backup: {e})")
ftp.storbinary("STOR htdocs/robots.txt", io.BytesIO(ROBOTS.encode()))
print("✅ robots.txt antigo → sitemap do domínio novo")

# 4. confere
buf = []
ftp.retrbinary("RETR htdocs/.htaccess", buf.append)
ok = b"R=301" in b"".join(buf) and NOVO.encode() in b"".join(buf)
print(f"{'✅' if ok else '❌'} verificação do redirect no .htaccess")
ftp.quit()
