#!/usr/bin/env python3
"""Lê o wp-sitemap.xml atravessando o challenge AES da InfinityFree.

Replica o solver _solve_challenge/_antibot_session de
dashboard/services/wordpress.py em stdlib pura (sem flask/httpx).
"""
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

SITE = "https://tech-tips.ct.ws"


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


def main():
    html = get(f"{SITE}/wp-sitemap.xml")
    if "toNumbers" not in html:
        print("SEM CHALLENGE — conteúdo direto:")
        urls = re.findall(r"<loc>(.*?)</loc>", html)
        print(f"Total URLs: {len(urls)}")
        for u in urls:
            print(" ", u)
        return

    cookie = solve_challenge(html)
    if not cookie:
        print("FALHOU ao resolver challenge")
        sys.exit(1)
    print(f"cookie __test resolvido")

    xml = get(f"{SITE}/wp-sitemap.xml", cookie=cookie)
    if "toNumbers" in xml:
        print("FALHOU: cookie não aceito")
        sys.exit(1)
    urls = re.findall(r"<loc>(.*?)</loc>", xml)
    print(f"---SITEMAP: {len(urls)} URLs---")
    for u in urls:
        print(" ", u)


if __name__ == "__main__":
    main()
