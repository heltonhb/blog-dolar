#!/usr/bin/env python3
"""Verifica se as páginas de conformidade do AdSense estão publicadas
no site https://techtips.dpdns.org (privacidade, termos, cookies, contato).

Usa antibot resolvendo o challenge AES da InfinityFree via Node + slowAES,
igual ao resto do projeto (scripts/antibot.py).
"""

import re
import sys
from pathlib import Path

# root do projeto (repo raiz)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import antibot

SITE = "https://techtips.dpdns.org"

# URLs prováveis de páginas de conformidade (wp-clean-urls)
CANDIDATOS = [
    "/privacy-policy/",
    "/privacy/",
    "/política-de-privacidade/",
    "/termos-de-uso/",
    "/termos-e-condicoes/",
    "/termos/",
    "/terms-and-conditions/",
    "/terms-of-service/",
    "/cookies/",
    "/politica-de-cookies/",
    "/contact/",
    "/contato/",
    "/about/",
    "/sobre/",
]


def main():
    html_inicio = antibot.get_pagina(f"{SITE}/")
    print(f"site inicial HTTP 200: {'✅' if html_inicio else '❌'}")
    if not html_inicio:
        print("  (não conseguiu carregar o site — abortando)")
        sys.exit(1)

    # puxa lista de páginas publicadas via REST
    try:
        posts_html = antibot.get_pagina(f"{SITE}/wp-json/wp/v2/pages?per_page=100")
        posts = __import__("json").loads(posts_html)
        print(f"páginas publicadas via REST: {len(posts)}")
        titulos = {p.get("slug", "") for p in posts if isinstance(p, dict)}
        print("  slugs de páginas:", sorted(titulos))
    except Exception as e:
        print(f"  (não pôde listar páginas via REST: {e})")
        titulos = set()

    print("\nTestando candidatos de conformidade:")
    ok = []
    falhou = []
    for path in CANDIDATOS:
        try:
            html = antibot.get_pagina(f"{SITE}{path}")
            status_text = "OK" if html else "vazio"
        except Exception as e:
            status_text = f"erro: {type(e).__name__}"
            html = ""
        presente = bool(html)
        if presente:
            ok.append(path)
            print(f"  ✅ {path}")
        else:
            falhou.append(path)
            print(f"  ❌ {path} — {status_text}")

    print("\nResumo:")
    if not ok:
        print("  nenhuma página de conformidade encontrada nos candidatos testados")
    else:
        print(f"  páginas encontradas: {len(ok)} de {len(CANDIDATOS)} candidatos")
        for p in ok:
            print(f"    - {SITE}{p}")

    # detecção básica de conteúdo de privacidade/termos dentro do HTML
    print("\nConteúdo sugerido de privacidade/termos dentro das páginas encontradas:")
    for path in ok:
        try:
            html = antibot.get_pagina(f"{SITE}{path}")
        except Exception:
            html = ""
        achou_privacidade = bool(re.search(r"privac|gdpr|cookies|dados pessoais|regulamenta", html, re.I))
        achou_termos = bool(re.search(r"termo|responsabilidade|isento|licença|propriedade|google|adsense|cookie", html, re.I))
        print(f"  {path}:")
        print(f"     privacidade-ish: {achou_privacidade} | termos-ish: {achou_termos}")


if __name__ == "__main__":
    main()
