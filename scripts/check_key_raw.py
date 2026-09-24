#!/usr/bin/env python3
"""O IndexNow vê a key SEM resolver o anti-bot? (como o bot do Bing veria)"""
import urllib.error
import urllib.request

key = "bcf6a1f7356bdd9c03994d747ba7aa49"
url = f"https://tech-tips.ct.ws/.well-known/{key}.txt"

req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        corpo = r.read().decode()
        print(f"HTTP {r.status} | corpo: {corpo[:80]!r}")
        print("✅ bot consegue ler a key" if corpo.strip() == key else "❌ conteúdo errado")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code} | corpo: {e.read().decode()[:100]!r}")
