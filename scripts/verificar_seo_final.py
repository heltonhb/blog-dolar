#!/usr/bin/env python3
"""Verificação final: todos os posts do sitemap devem ter GA4 + meta description + og tags."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import httpx

SITE = "https://tech-tips.ct.ws"


def _env(key, default=""):
    for line in open(os.path.join(ROOT, ".env")):
        line = line.strip()
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return default


def antibot_client():
    from ler_sitemap import solve_challenge
    domain = "tech-tips.ct.ws"
    client = httpx.Client(timeout=30, verify=False, follow_redirects=True)
    resp = client.get(f"{SITE}/", timeout=20)
    if "toNumbers" in resp.text and "slowAES" in resp.text:
        cookie = solve_challenge(resp.text)
        client.cookies.set("__test", cookie, domain=domain)
    return client


def main():
    client = antibot_client()
    # puxa todos os posts publicados via REST
    r = client.get(f"{SITE}/wp-json/wp/v2/posts", params={"per_page": 100})
    posts = r.json()
    print(f"{len(posts)} posts publicados")
    all_ok = True
    for p in posts:
        link = p["link"]
        page = client.get(link, timeout=20)
        html = page.text
        ga4 = "G-G01J573W6J" in html and "googletagmanager" in html
        metadesc = bool(re.search(r'<meta name="description"', html))
        og_desc = 'property="og:description"' in html
        ok = ga4 and metadesc and og_desc
        all_ok = all_ok and ok
        status = "OK " if ok else "FALHOU"
        print(f"  [{status}] {link} GA4={ga4} metadesc={metadesc} og={og_desc}")
    print(f"\nTODOS OK: {all_ok}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
