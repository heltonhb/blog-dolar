#!/usr/bin/env python3
"""Migração Plano G — etapa 1: wp-config do addon aponta pro banco antigo.

O WP do addon passa a usar if042797779_wp631 + prefixo wptl_ (os mesmos do
site atual). Backup do wp-config novo (Softaculous) fica salvo localmente.
"""
import io
import os
import re
from pathlib import Path

import ftplib
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=20)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))

CFG_ADDON = "techtips.dpdns.org/htdocs/wp-config.php"

# 1. baixa o wp-config novo (base — tem os defines de auth/salt do Softaculous)
buf = []
ftp.retrbinary(f"RETR {CFG_ADDON}", buf.append)
cfg = b"".join(buf).decode(errors="replace")

# guarda backup local
Path("scripts/_backup_wpconfig_addon_softaculous.php").write_text(cfg)
print("✅ backup local do wp-config (Softaculous) salvo")

# 2. troca banco, usuário e prefixo
subs = {
    r"(define\(\s*'DB_NAME'\s*,\s*')[^']+(')": r"\g<1>if042797779_wp631\g<2>",
    r"(define\(\s*'DB_USER'\s*,\s*')[^']+(')": r"\g<1>42797779_1\g<2>",
    r"(\$table_prefix\s*=\s*')[^']+(')": r"\g<1>wptl_\g<2>",
}
for padrao, repl in subs.items():
    cfg, n = re.subn(padrao, repl, cfg)
    print(f"   {'✅' if n == 1 else '❌'} substituição ({n}x)")

# 3. WP_HOME/WP_SITEURL explícitos no config (mais confiável que o banco
#    na primeira carga — evita redirect p/ o domínio antigo)
if "WP_HOME" not in cfg:
    cfg = re.sub(
        r"(\$table_prefix\s*=\s*'[^']+';)",
        r"\1\n\ndefine('WP_HOME', 'https://techtips.dpdns.org');\n"
        r"define('WP_SITEURL', 'https://techtips.dpdns.org');",
        cfg,
    )
    print("   ✅ WP_HOME/WP_SITEURL definidos")

# 4. reenvia
ftp.storbinary(f"STOR {CFG_ADDON}", io.BytesIO(cfg.encode()))
print("✅ wp-config do addon atualizado")

# 5. confere
buf = []
ftp.retrbinary(f"RETR {CFG_ADDON}", buf.append)
final = b"".join(buf).decode(errors="replace")
ok = (
    "if042797779_wp631" in final
    and "wptl_" in final
    and "techtips.dpdns.org" in final
)
print(f"{'✅' if ok else '❌'} verificação: banco antigo + prefixo + domínio novo no config")
ftp.quit()
