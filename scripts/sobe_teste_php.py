#!/usr/bin/env python3
"""Onde está o wp-blog-header.php de verdade? Varre candidatos via PHP."""
import io
import os
import sys
import urllib.request
from pathlib import Path

import ftplib
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
import antibot  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

ftp = ftplib.FTP(os.environ.get("FTP_HOST", "ftpupload.net"), timeout=20)
ftp.login(os.environ.get("FTP_USER", ""), os.environ.get("FTP_PASS", ""))

TESTE = """<?php
header('Content-Type: text/plain');
$cand = [
  '/home/vol6_1/infinityfree.com/if0_42797779/htdocs/wp-blog-header.php',
  '/home/vol6_1/infinityfree.com/if0_42797779/techtips.dpdns.org/htdocs/wp-blog-header.php',
  '/htdocs/wp-blog-header.php',
  dirname(__DIR__, 2) . '/htdocs/wp-blog-header.php',
  dirname(__DIR__, 3) . '/htdocs/wp-blog-header.php',
];
foreach ($cand as $c) {
  echo (file_exists($c) ? 'EXISTE  ' : 'não     ') . $c . "\\n";
}
echo "\\n scandir raiz da conta:\\n";
foreach (scandir(dirname(__DIR__, 2)) as $f) echo "  $f\\n";
echo "scandir /htdocs da conta:\\n";
foreach (scandir(dirname(__DIR__, 2) . '/htdocs') as $f) echo "  $f\\n";
"""

ftp.storbinary("STOR techtips.dpdns.org/htdocs/_teste.php", io.BytesIO(TESTE.encode()))
ftp.quit()
print("teste atualizado")

# executa
antibot.SITE = "http://techtips.dpdns.org"
url = "http://techtips.dpdns.org/_teste.php"
html = antibot.get(url)
if "toNumbers" in html:
    cookie = antibot.solve_challenge(html)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Cookie": f"__test={cookie}"})
    print(urllib.request.urlopen(req, timeout=30).read().decode(errors="replace"))
else:
    print(html)
