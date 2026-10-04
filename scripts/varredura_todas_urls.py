#!/usr/bin/env python3
"""Varredura de anúncios em TODAS as URLs vivas do site (posts + páginas).

Saída: uma linha por URL com contagem de scripts de anúncio (esperado: 0)
e veredito. Também confere GA4 e links internos como bonus de sanidade.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from antibot import get_pagina  # noqa: E402
from fetch_urls import fetch_post_urls  # noqa: E402

SITE = "https://techtips.dpdns.org"

PAGINAS_UTEIS = [
    "/",
    "/privacy-policy/",
    "/terms-of-service/",
    "/about-us/",
    "/contact/",
]

PADRAO_AD = re.compile(r"profitablerate|pl314\d+|adsterra", re.I)


def varrer(url: str) -> tuple[bool, int, int]:
    """(limpo?, n_scripts_ad, n_scripts_total)"""
    html = get_pagina(url)
    scripts = re.findall(r"<script[^>]*src=[\"']([^\"']+)[\"']", html)
    ads = [s for s in scripts if PADRAO_AD.search(s)]
    # também procura inline (caso algum resto tenha ficado inline)
    ads_inline = len(re.findall(r"profitablerate|container-27e8efa", html))
    return (len(ads) == 0 and ads_inline == 0), len(ads) + ads_inline, len(scripts)


def main():
    posts = fetch_post_urls()
    todas = [(u, "post") for u in posts] + [
        (f"{SITE}{p}", "página") for p in PAGINAS_UTEIS
    ]

    limpos = 0
    problemas = []
    for url, tipo in todas:
        try:
            limpo, n_ads, n_scripts = varrer(url)
        except Exception as e:  # noqa: BLE001
            print(f"⚠️  {tipo:<6} {url}: ERRO {type(e).__name__}: {e}")
            problemas.append((url, str(e)))
            continue
        slug = url.rstrip("/").split("/")[-1][:52]
        simb = "🟢" if limpo else "🔴"
        print(f"{simb} {tipo:<6} {slug:<54} ads: {n_ads} | scripts: {n_scripts}")
        limpos += limpo

    print(f"\n{limpos}/{len(todas)} URLs limpas de anúncios")
    if problemas:
        print("URLs com erro de fetch:", len(problemas))
    return 0 if (not problemas and limpos == len(todas)) else 1


if __name__ == "__main__":
    sys.exit(main())
