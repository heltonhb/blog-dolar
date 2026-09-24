#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Relatório semanal de indexação — tech-tips.ct.ws (Search Console).

Cruza o sitemap vivo com a URL Inspection API:
  1. Baixa wp-sitemap.xml + filhos (atravessa o challenge AES da
     InfinityFree com o solver de scripts/ler_sitemap.py).
  2. Inspeciona cada URL: veredito, cobertura, último crawl, motivos.
  3. Grava:
       dashboard/data/indexacao_relatorio.json  (dados p/ consumo)
       dashboard/data/indexacao_relatorio.md    (relatório legível)
  4. Compara com a última execução e destaca mudanças de status.

Uso:
  python scripts/relatorio_indexacao.py      # roda tudo e gera o relatório
  python scripts/relatorio_indexacao.py --ler  # reimprime o último salvo

Auth: mesma de scripts/check_indexacao.py (OAuth de usuário no .env).
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
DATA_DIR = PROJECT_ROOT / "dashboard" / "data"
JSON_OUT = DATA_DIR / "indexacao_relatorio.json"
MD_OUT = DATA_DIR / "indexacao_relatorio.md"

SITE = "https://tech-tips.ct.ws"
SITE_SC = "https://tech-tips.ct.ws/"  # siteUrl registrado no Search Console


def _import_deps():
    sys.path.insert(0, str(SCRIPTS_DIR))
    from check_indexacao import get_access_token
    from ler_sitemap import get as http_get, solve_challenge
    return get_access_token, http_get, solve_challenge


def fetch_sitemap_urls(http_get, solve_challenge) -> list:
    """Índice + filhos do sitemap, passando pelo antibot da InfinityFree."""
    html = http_get(f"{SITE}/wp-sitemap.xml")
    cookie = ""
    if "toNumbers" in html:
        cookie = solve_challenge(html)
        if not cookie:
            raise SystemExit("❌ FALHOU ao resolver o challenge antibot")
        html = http_get(f"{SITE}/wp-sitemap.xml", cookie=cookie)

    def locs(xml):
        return re.findall(r"<loc>(.*?)</loc>", xml)

    if "<sitemapindex" in html:
        urls = []
        for child in locs(html):
            xml = http_get(child, cookie=cookie)
            if "toNumbers" in xml:  # cookie expirou no meio do caminho
                cookie = solve_challenge(xml)
                xml = http_get(child, cookie=cookie)
            urls.extend(locs(xml))
    else:
        urls = locs(html)
    return list(dict.fromkeys(urls))


def classifica(cobertura: str) -> str:
    c = cobertura.lower()
    if "enviada e indexada" in c:
        return "indexada"
    if "não reconhece" in c:
        return "desconhecida"
    return "nao_indexada"


def inspect_url(token: str, url: str) -> dict:
    body = json.dumps({
        "inspectionUrl": url,
        "siteUrl": SITE_SC,
        "languageCode": "pt-BR",
    }).encode()
    req = urllib.request.Request(
        "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"url": url, "status": "erro",
                "erro": f"HTTP {e.code}: {e.read().decode(errors='replace')[:150]}"}
    idx = data.get("inspectionResult", {}).get("indexStatusResult", {})
    cobertura = idx.get("coverageState", "?")
    return {
        "url": url,
        "status": classifica(cobertura),
        "veredito": idx.get("verdict", "?"),
        "cobertura": cobertura,
        "ultimo_crawl": idx.get("lastCrawlTime", ""),
        "motivos": idx.get("reasons", []),
    }


def diff_previous(previous: dict, results: list) -> dict:
    prev = {r["url"]: r.get("status") for r in previous.get("urls", [])}
    cur = {r["url"]: r.get("status") for r in results}
    return {
        "melhoraram": [u for u, s in cur.items()
                       if prev.get(u) not in (None, "indexada") and s == "indexada"],
        "pioraram": [u for u, s in cur.items()
                      if prev.get(u) == "indexada" and s != "indexada"],
        "novas": [u for u in cur if u not in prev],
        "removidas": [u for u in prev if u not in cur],
    }


def write_report(results: list, changes: dict, prev_date: str) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "gerado_em": datetime.now().isoformat(),
        "site": SITE_SC,
        "resumo": {
            "total": len(results),
            "indexadas": sum(1 for r in results if r.get("status") == "indexada"),
            "nao_indexadas": sum(1 for r in results if r.get("status") == "nao_indexada"),
            "desconhecidas": sum(1 for r in results if r.get("status") == "desconhecida"),
        },
        "comparado_com": prev_date,
        "diff": changes,
        "urls": results,
    }
    JSON_OUT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    res = report["resumo"]
    linhas = [
        "# Relatório de indexação — tech-tips.ct.ws",
        "",
        f"Gerado em {report['gerado_em'][:19].replace('T', ' ')}",
        "",
        "## Resumo",
        f"- Enviadas e indexadas: **{res['indexadas']}/{res['total']}**",
        f"- Detectadas, mas não indexadas: {res['nao_indexadas']}",
        f"- Não reconhecidas pelo Google: {res['desconhecidas']}",
        "",
        f"## Mudanças desde {prev_date or '(primeira execução)'}",
    ]
    if changes["melhoraram"]:
        linhas.append(f"- ✅ Passaram a indexadas ({len(changes['melhoraram'])}): "
                     + ", ".join(changes["melhoraram"]))
    if changes["pioraram"]:
        linhas.append(f"- ⚠️ Deixaram de ser indexadas ({len(changes['pioraram'])}): "
                     + ", ".join(changes["pioraram"]))
    if changes["novas"]:
        linhas.append(f"- 🆕 URLs novas no sitemap ({len(changes['novas'])}): "
                     + ", ".join(changes["novas"]))
    if changes["removidas"]:
        linhas.append(f"- 🗑️ Sairam do sitemap ({len(changes['removidas'])}): "
                     + ", ".join(changes["removidas"]))
    if not any(changes.values()):
        linhas.append("- Nenhuma mudança de status.")
    linhas += ["", "## Detalhe por URL", "",
               "| URL | cobertura | último crawl |", "|---|---|---|"]
    for r in results:
        crawl = (r.get("ultimo_crawl") or "nunca")[:16].replace("T", " ")
        linhas.append(f"| {r['url']} | {r.get('cobertura', r.get('status'))} | {crawl} |")
    MD_OUT.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="Relatório de indexação Search Console")
    parser.add_argument("--ler", action="store_true",
                        help="Só reimprime o último relatório salvo")
    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)  # check_indexacao lê .env relativo ao CWD

    if args.ler:
        if not MD_OUT.exists():
            raise SystemExit("Ainda não há relatório salvo. Rode sem --ler primeiro.")
        print(MD_OUT.read_text(encoding="utf-8"))
        return

    get_access_token, http_get, solve_challenge = _import_deps()
    token, _ = get_access_token("webmasters")

    urls = fetch_sitemap_urls(http_get, solve_challenge)
    print(f"Sitemap: {len(urls)} URLs")
    results = []
    for i, url in enumerate(urls, 1):
        print(f"  [{i}/{len(urls)}] {url}")
        results.append(inspect_url(token, url))
        time.sleep(0.5)

    previous: dict = {}
    prev_date: str = ""
    if JSON_OUT.exists():
        try:
            previous = json.loads(JSON_OUT.read_text(encoding="utf-8"))
            prev_date = str((previous.get("gerado_em") or ""))[:19]
        except Exception:
            previous = {}

    changes = (diff_previous(previous, results) if previous
               else {"melhoraram": [], "pioraram": [], "novas": [], "removidas": []})
    report = write_report(results, changes, prev_date)

    res = report["resumo"]
    print(f"\n=== Resumo ({report['gerado_em'][:19]}) ===")
    print(f"  indexadas: {res['indexadas']}/{res['total']}"
          f"  |  não indexadas: {res['nao_indexadas']}"
          f"  |  desconhecidas: {res['desconhecidas']}")
    if changes["melhoraram"]:
        print(f"  ✅ melhoraram: {len(changes['melhoraram'])}")
    if changes["pioraram"]:
        print(f"  ⚠️ pioraram: {len(changes['pioraram'])}")
    print(f"\nRelatórios salvos em:\n  {JSON_OUT}\n  {MD_OUT}")


if __name__ == "__main__":
    main()
