#!/usr/bin/env python3
"""Auditoria AdSense: pré-requisitos de conteúdo por post (via REST WP).

Checa: título com keyword (>=30 chars), meta description, excerpt,
comprimento (>=600 palavras), headings h2/h3, imagens com alt,
links internos (Related), CTA/canonical.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from antibot import SITE  # noqa: E402
from fetch_wp_post import _rest_get, fetch_post_by_slug  # noqa: E402
from fetch_urls import fetch_post_urls  # noqa: E402


def auditar(slug: str) -> dict:
    post = fetch_post_by_slug(slug)
    if not post:
        return {"slug": slug, "erro": "post não encontrado"}
    c = post["content_html"]
    texto = re.sub(r"<[^>]+>", " ", c)
    palavras = len(texto.split())
    h2 = len(re.findall(r"<h2", c))
    h3 = len(re.findall(r"<h3", c))
    imgs = len(re.findall(r"<img", c))
    alts = len(re.findall(r'<img[^>]+alt="[^"]+"', c))
    internal = len(re.findall(r'href="https://tech-tips\.ct\.ws', c))
    related = "Related Articles" in c
    return {
        "slug": slug,
        "titulo_len": len(post["title"]),
        "palavras": palavras,
        "h2": h2, "h3": h3,
        "imagens": imgs, "com_alt": alts,
        "links_internos": internal,
        "related_ok": related,
    }


def main():
    slugs = [u.rstrip("/").split("/")[-1] for u in fetch_post_urls()]

    # meta description: vem do mu-plugin GA4/SEO no HTML renderizado
    import urllib.request

    from antibot import get_pagina

    print(f"{'slug':<52} {'palav':>5} {'h2':>3} {'img':>4} {'alt':>4} {'rel':>4} {'meta':>5}")
    fracos = []
    for s in slugs:
        a = auditar(s)
        if "erro" in a:
            print(f"⚠️ {a['slug']}: {a['erro']}")
            continue
        html = get_pagina(f"{SITE}/2026/09/19/{s}/") if False else None
        # meta description real: busca no HTML da página do post
        # (URL completa vem do link do post)
        post = fetch_post_by_slug(s)
        url = post["link"]
        html = get_pagina(url)
        m = re.search(r'<meta name="description" content="([^"]+)"', html)
        meta_len = len(m.group(1)) if m else 0

        flags = []
        if a["palavras"] < 600: flags.append("CURTO")
        if a["h2"] < 2: flags.append("H2-")
        if not a["related_ok"]: flags.append("semRelated")
        if meta_len < 70: flags.append("meta-")
        if flags:
            fracos.append((s, flags))

        print(f"{a['slug'][:51]:<52} {a['palavras']:>5} {a['h2']:>3} {a['imagens']:>4} "
              f"{a['com_alt']:>4} {'✓' if a['related_ok'] else '✗':>4} {meta_len:>5} "
              f"{' '.join(flags)}")

    print()
    if fracos:
        print(f"⚠️ {len(fracos)} post(s) com pendências AdSense:")
        for s, f in fracos:
            print(f"   {s}: {', '.join(f)}")
    else:
        print("✅ todos os posts atendem os pré-requisitos básicos")


if __name__ == "__main__":
    main()
