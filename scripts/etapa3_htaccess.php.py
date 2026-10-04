#!/usr/bin/env python3
"""Etapa 3 da migração: .htaccess correto do addon.

- Permalinks do WP (/%year%/%monthnum%/%day%/%postname%/)
- SEM as regras W3TC mortas que o Softaculous herdade
- Redirect do http→https fica pro SSL/painel (mod_rewrite do R:: pode
  conflitar com o anti-bot deles — testamos antes)
"""
import io
import os
from pathlib import Path

import ftplib
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

HTACCESS = """# BEGIN WordPress
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteBase /
RewriteRule ^index\\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.php [L]
</IfModule>
# END WordPress
"""

ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=30)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))

# backup do atual (W3TC herdado)
buf = []
try:
    ftp.retrbinary("RETR techtips.dpdns.org/htdocs/.htaccess", buf.append)
    Path("scripts/_backup_htaccess_addon_w3tc").write_text(b"".join(buf).decode(errors="replace"))
    print("✅ backup do .htaccess W3TC salvo localmente")
except Exception as e:  # noqa: BLE001
    print(f"(backup: {e})")

ftp.storbinary("STOR techtips.dpdns.org/htdocs/.htaccess", io.BytesIO(HTACCESS.encode()))
print("✅ .htaccess novo (permalinks WP) enviado")

buf = []
ftp.retrbinary("RETR techtips.dpdns.org/htdocs/.htaccess", buf.append)
ok = b"BEGIN WordPress" in b"".join(buf)
print(f"{'✅' if ok else '❌'} verificado")
ftp.quit()
