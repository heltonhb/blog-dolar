#!/usr/bin/env python3
"""Sobe o probe de open_basedir e executa."""
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

probe = Path("scripts/_probe_basedir.php").read_text()
ftp.storbinary("STOR techtips.dpdns.org/htdocs/_probe.php", io.BytesIO(probe.encode()))
ftp.quit()
print("probe enviado")

antibot.SITE = "http://techtips.dpdns.org"
url = "http://techtips.dpdns.org/_probe.php"
html = antibot.get(url)
if "toNumbers" in html:
    cookie = antibot.solve_challenge(html)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Cookie": f"__test={cookie}"})
    print(urllib.request.urlopen(req, timeout=30).read().decode(errors="replace"))
else:
    print(html)
