#!/usr/bin/env python3
"""IndexNow corrigido: resolve anti-bot do sitemap e submete URLs.

Google NÃO usa IndexNow (usa Search Console). Bing/Yandex/Naver sim.
"""
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from antibot import get_pagina  # noqa: E402
from fetch_urls import fetch_post_urls  # noqa: E402

HOST = "tech-tips.ct.ws"
KEY_FILE = Path(__file__).parent.parent / ".well-known" / "indexnow-key.txt"


def obter_key() -> str:
    """Key estável, salva no .well-known/ (o arquivo sobe via FTP uma vez)."""
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    key = hashlib.md5(f"{HOST}-indexnow".encode()).hexdigest()
    KEY_FILE.parent.mkdir(exist_ok=True)
    KEY_FILE.write_text(key)
    print(f"🔑 Key gerada: {key}")
    print(f"   → subir via FTP: htdocs/.well-known/{key}.txt (conteúdo: a key)")
    return key


def main():
    urls = fetch_post_urls()
    print(f"📄 {len(urls)} URLs de posts")

    key = obter_key()

    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": f"https://{HOST}/.well-known/{key}.txt",
        "urlList": urls,
    }
    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "blog-dolar-seo/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"✅ IndexNow HTTP {r.status} — {len(urls)} URLs aceitas (Bing/Yandex/Naver)")
    except urllib.error.HTTPError as e:
        print(f"⚠️ IndexNow HTTP {e.code} — {e.read().decode()[:200]}")


if __name__ == "__main__":
    main()
