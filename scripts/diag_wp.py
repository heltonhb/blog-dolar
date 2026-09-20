#!/usr/bin/env python3
"""Diagnóstico rápido do WP: plugins instalados e lista de posts.

Usa o _antibot_session do projeto (httpx) via terminal com o venv/dependências
do projeto — dashboard.services.wordpress importa flask indiretamente.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

# httpx disponível? (requirements do projeto)
try:
    import httpx  # noqa: F401
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

SITE = "https://tech-tips.ct.ws"


def _env(key, default=""):
    for line in open(".env"):
        line = line.strip()
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return default


def solve_challenge_stdlib(html):
    """Replica _solve_challenge em stdlib (urllib + node)."""
    matches = re.findall(r'toNumbers\("([0-9a-f]+)"\)', html)
    if len(matches) < 3:
        return None
    a, b, c = matches[0], matches[1], matches[2]
    req = urllib.request.Request(f"{SITE}/aes.js", headers={"User-Agent": "Mozilla/5.0"})
    aes_js = urllib.request.urlopen(req, timeout=30).read().decode(errors="replace")
    node_code = (
        aes_js + "\n"
        'function toNumbers(d){var e=[];d.replace(/(..)/g,function(d){e.push(parseInt(d,16))});return e}\n'
        'function toHex(){for(var d=[],d=1==arguments.length&&arguments[0].constructor==Array?arguments[0]:arguments,e="",f=0;f<d.length;f++)e+=(16>d[f]?"0":"")+d[f].toString(16);return e.toLowerCase()}\n'
        f'var a=toNumbers("{a}"),b=toNumbers("{b}"),c=toNumbers("{c}");\n'
        'console.log(toHex(slowAES.decrypt(c,2,a,b)));\n'
    )
    tmpfile = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(node_code)
            tmpfile = f.name
        result = subprocess.run(["node", tmpfile], capture_output=True, text=True, timeout=10)
        cookie = result.stdout.strip()
        return cookie if cookie else None
    finally:
        if tmpfile:
            try:
                os.unlink(tmpfile)
            except OSError:
                pass


def wp_session():
    """httpx.Client com cookie anti-bot, ou None se falhar."""
    import httpx
    domain = "tech-tips.ct.ws"
    client = httpx.Client(timeout=30, verify=False, follow_redirects=True)
    resp = client.get(f"{SITE}/", timeout=15)
    html = resp.text
    if "toNumbers" in html and "slowAES" in html:
        cookie_val = solve_challenge_stdlib(html)
        if not cookie_val:
            print("FALHOU: challenge não resolvido")
            sys.exit(1)
        client.cookies.set("__test", cookie_val, domain=domain)
    return client


def main():
    print(f"httpx disponível: {HAS_HTTPX}")
    wp_user = _env("WP_USER")
    wp_pass = _env("WP_APP_PASSWORD")
    print(f"WP_USER: {wp_user[:4]}*** (app password: {'ok' if wp_pass else 'FALTA'})")

    client = wp_session()
    auth = (wp_user, wp_pass)

    # 1. Teste de auth no REST
    r = client.get(f"{SITE}/wp-json/wp/v2/users/me", auth=auth)
    print(f"\nusers/me: HTTP {r.status_code}")
    if r.status_code == 200:
        me = r.json()
        print(f"  autenticado como: {me.get('name')} (roles: {me.get('roles', [])})")

    # 2. Plugins instalados
    r = client.get(f"{SITE}/wp-json/wp/v2/plugins")
    try:
        plugins = r.json()
        print(f"\nplugins (HTTP {r.status_code}):")
        if isinstance(plugins, list):
            for p in plugins:
                print(f"  {p.get('plugin')} — {p.get('status')}")
        else:
            print(f"  {str(plugins)[:150]}")
    except Exception:
        print(f"  resposta não-JSON: {r.status_code} {r.text[:100]}")

    # 3. Posts (busca com status any p/ ver também rascunhos)
    print("\nposts (status=publish):")
    r = client.get(f"{SITE}/wp-json/wp/v2/posts", params={"per_page": 100, "status": "publish"})
    posts = r.json()
    if isinstance(posts, list):
        for p in posts:
            print(f"  [{p.get('id')}] {p.get('slug')} — excerpt: {p.get('excerpt', {}).get('rendered', '')[:60]!r}")
    else:
        print(f"  erro: {str(posts)[:150]}")


if __name__ == "__main__":
    main()
