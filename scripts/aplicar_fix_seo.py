#!/usr/bin/env python3
"""Passos 1-3 da correção de SEO:

1. Sobe mu-plugin tech-tips-ga4-seo.php via FTP (GA4 + meta description/og)
2. Deleta o post "hello-world" (ID 1, sample do WP) via REST
3. Verifica: HTML publicado contém GA4 + meta description + post sumiu

Uso: .venv/bin/python scripts/aplicar_fix_seo.py
"""
import io
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import ftplib
import httpx

SITE = "https://tech-tips.ct.ws"
MUPLUGIN_LOCAL = os.path.join(ROOT, "scripts", "tech-tips-ga4-seo.php")
MUPLUGIN_REMOTE = "htdocs/wp-content/mu-plugins/tech-tips-ga4-seo.php"


def _env(key, default=""):
    for line in open(os.path.join(ROOT, ".env")):
        line = line.strip()
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return default


def antibot_client() -> httpx.Client:
    domain = "tech-tips.ct.ws"
    client = httpx.Client(timeout=30, verify=False, follow_redirects=True)
    resp = client.get(f"{SITE}/", timeout=20)
    html = resp.text
    if "toNumbers" in html and "slowAES" in html:
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        from ler_sitemap import solve_challenge
        cookie = solve_challenge(html)
        if not cookie:
            raise RuntimeError("challenge anti-bot não resolvido")
        client.cookies.set("__test", cookie, domain=domain)
        # valida
        test = client.get(f"{SITE}/wp-json/", timeout=15)
        if test.status_code != 200:
            raise RuntimeError("cookie anti-bot rejeitado")
    return client


def ftp_upload_muplugin():
    print("=== PASSO 1: mu-plugin GA4+SEO via FTP ===")
    ftp = ftplib.FTP(_env("FTP_HOST"), timeout=20)
    ftp.login(_env("FTP_USER"), _env("FTP_PASS"))
    try:
        ftp.cwd("htdocs/wp-content/mu-plugins")
        with open(MUPLUGIN_LOCAL, "rb") as f:
            ftp.storbinary(f"STOR tech-tips-ga4-seo.php", f)
        # confirma
        listing = ftp.nlst()
        print("  arquivos em mu-plugins:", listing)
        # tamanho bate?
        size_remote = ftp.size("tech-tips-ga4-seo.php")
        size_local = os.path.getsize(MUPLUGIN_LOCAL)
        print(f"  tamanho local={size_local} remoto={size_remote}")
        if size_remote != size_local:
            print("  AVISO: tamanho divergente!")
            return False
        return True
    finally:
        ftp.quit()


def delete_hello_world(client):
    print("\n=== PASSO 3: deletar hello-world ===")
    auth = (_env("WP_USER"), _env("WP_APP_PASSWORD"))
    # localiza o post pelo slug (ID pode variar)
    r = client.get(f"{SITE}/wp-json/wp/v2/posts", params={"slug": "hello-world", "status": "any"}, auth=auth)
    posts = r.json()
    if not isinstance(posts, list) or not posts:
        print("  'hello-world' não encontrado (já deletado?)")
        return True
    pid = posts[0]["id"]
    print(f"  encontrado: ID {pid} — '{posts[0]['title']['rendered']}'")
    r = client.delete(f"{SITE}/wp-json/wp/v2/posts/{pid}", auth=auth, params={"force": "true"})
    if r.status_code == 200:
        deleted = r.json().get("deleted", r.json().get("data", {}).get("status"))
        print(f"  deletado: {deleted}")
        return True
    print(f"  ERRO HTTP {r.status_code}: {r.text[:200]}")
    return False


def verify_front_end(client):
    print("\n=== VERIFICAÇÃO DO FRONT-END ===")
    ok = True
    for url in [f"{SITE}/", f"{SITE}/2026/09/19/quantum-computing-2026/"]:
        r = client.get(url, timeout=20)
        html = r.text
        ga4 = "G-G01J573W6J" in html and "googletagmanager" in html
        metadesc = 'name="description"' in html
        og = 'property="og:description"' in html
        wp_alive = r.status_code == 200 and "fatal error" not in html.lower()
        print(f"  {url}")
        print(f"    HTTP {r.status_code} | site no ar: {wp_alive} | GA4: {ga4} | meta description: {metadesc} | og: {og}")
        ok = ok and wp_alive and ga4 and metadesc and og
    return ok


def verify_hello_gone(client):
    r = client.get(f"{SITE}/wp-json/wp/v2/posts", params={"slug": "hello-world", "status": "any"})
    posts = r.json()
    gone = not (isinstance(posts, list) and posts)
    print(f"  hello-world removido da listagem: {gone}")
    return gone


if __name__ == "__main__":
    step1 = ftp_upload_muplugin()
    # pequena pausa — mu-plugin é lido a cada request, sem cache de opcodes conhecido
    time.sleep(2)
    client = antibot_client()
    step3 = delete_hello_world(client)
    time.sleep(2)
    v_front = verify_front_end(client)
    v_hello = verify_hello_gone(client)
    print("\n=== RESUMO ===")
    print(f"  mu-plugin subido: {step1}")
    print(f"  hello-world deletado: {step3}")
    print(f"  front-end verificado (GA4+meta): {v_front}")
    print(f"  hello-world fora do ar: {v_hello}")
    sys.exit(0 if (step1 and step3 and v_front and v_hello) else 1)
