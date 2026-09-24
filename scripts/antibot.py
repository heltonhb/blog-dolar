#!/usr/bin/env python3
"""Ferramenta anti-bot: resolve o challenge AES da InfinityFree em stdlib.

O cookie __test vale 6h (max-age=21600) — resolvemos UMA vez por processo
e reutilizamos em todas as chamadas (a InfinityFree limita requisições
seguidas; re-solver por chamada vira rate-limit).
"""
import os
import re
import subprocess
import tempfile
import urllib.request

SITE = "https://tech-tips.ct.ws"

_cookie_cache: str = ""


def get(url: str, cookie: str = "") -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    if cookie:
        headers["Cookie"] = f"__test={cookie}"
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=30).read().decode(errors="replace")


def solve_challenge(html: str) -> str:
    """Resolve o challenge AES: baixa aes.js do site e roda slowAES no Node."""
    matches = re.findall(r'toNumbers\("([0-9a-f]+)"\)', html)
    if len(matches) < 3:
        return ""
    a, b, c = matches[0], matches[1], matches[2]

    aes_js = get(f"{SITE}/aes.js")
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
        return result.stdout.strip()
    finally:
        if tmpfile:
            try:
                os.unlink(tmpfile)
            except OSError:
                pass


def obter_cookie(force: bool = False) -> str:
    """Cookie __test resolvido, cacheado no processo (válido por 6h)."""
    global _cookie_cache
    if _cookie_cache and not force:
        return _cookie_cache
    html = get(f"{SITE}/wp-sitemap.xml")
    if "toNumbers" not in html:  # sem challenge ativo
        _cookie_cache = ""
        return ""
    cookie = solve_challenge(html)
    if cookie:
        _cookie_cache = cookie
    return cookie


def get_pagina(url: str) -> str:
    """GET atravessando o anti-bot com o cookie cacheado."""
    global _cookie_cache
    cookie = obter_cookie()
    html = get(url, cookie=cookie) if cookie else get(url)
    if "toNumbers" in html and cookie != "":
        # cookie expirou no meio do caminho — resolve de novo, uma vez
        cookie = obter_cookie(force=True)
        html = get(url, cookie=cookie)
    if "toNumbers" in html:
        raise RuntimeError(f"anti-bot: cookie não aceito para {url}")
    return html


if __name__ == "__main__":
    import sys
    print(get_pagina(sys.argv[1] if len(sys.argv) > 1 else f"{SITE}/wp-sitemap.xml"))
