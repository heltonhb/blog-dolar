#!/usr/bin/env python3
"""Corrige o bootstrap do addon com caminho absoluto à prova de erro."""
import io
import os
from pathlib import Path

import ftplib
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=20)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))

# Caminho absoluto visto no painel: /home/vol6_1/infinityfree.com/if0_42797779/...
# index.php está em .../if0_42797779/techtips.dpdns.org/htdocs/
# WP está em        .../if0_42797779/htdocs/
INDEX = """<?php
/**
 * Bootstrap: este addon domain serve o WordPress instalado em /htdocs.
 * Caminho absoluto — à prova de mudança de estrutura de pastas.
 */
define('WP_USE_THEMES', true);
require '/home/vol6_1/infinityfree.com/if0_42797779/htdocs/wp-blog-header.php';
"""

ftp.storbinary("STOR techtips.dpdns.org/htdocs/index.php", io.BytesIO(INDEX.encode()))
print("✅ bootstrap reenviado com caminho absoluto")

buf = []
ftp.retrbinary("RETR techtips.dpdns.org/htdocs/index.php", buf.append)
print(b"".join(buf).decode(errors="replace")[-120:])
ftp.quit()
