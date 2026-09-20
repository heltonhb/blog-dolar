#!/usr/bin/env python3
"""Verifica sitemaps e indexação no Search Console + site ao vivo."""
import json
import sys
import urllib.request
import urllib.parse
import urllib.error

sys.path.insert(0, "scripts")
from check_indexacao import get_access_token, api_get


def check_site_live():
    print("\n=== SITE AO VIVO ===")
    for path in ("/", "/robots.txt", "/sitemap.xml", "/sitemap.php", "/google36841e3dc65b42a5.html"):
        url = f"https://tech-tips.ct.ws{path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read(500).decode(errors="replace")
                print(f"  {path}: HTTP {r.status} — {body[:120]!r}")
        except urllib.error.HTTPError as e:
            print(f"  {path}: HTTP {e.code}")
        except Exception as e:
            print(f"  {path}: ERRO {type(e).__name__}: {e}")


def check_sitemaps(token):
    print("\n=== SITEMAPS NO SEARCH CONSOLE ===")
    target = "https://tech-tips.ct.ws/"
    api_path = urllib.parse.quote(target, safe="")
    data, code = api_get(
        f"https://www.googleapis.com/webmasters/v3/sites/{api_path}/sitemaps", token
    )
    if code == 200:
        sm = data.get("sitemap", [])
        if not sm:
            print("  Nenhum sitemap submetido")
        for s in sm:
            print(f"  {s.get('path')} — {s.get('state')} "
                  f"(enviados: último ok {s.get('lastDownloaded', 'nunca')}, "
                  f"conteudos: {s.get('contents', [])})")
    else:
        print(f"  erro {code}: {json.dumps(data)[:200]}")


def check_daily_impressions(token):
    """Dados dia a dia para achar quando as impressões começaram."""
    print("\n=== IMPRESSÕES DIA A DIA (últimos 30 dias) ===")
    target = "https://tech-tips.ct.ws/"
    api_path = urllib.parse.quote(target, safe="")
    body = json.dumps({
        "startDate": "2026-08-20",
        "endDate": "2026-09-19",
        "dimensions": ["date"],
        "rowLimit": 31,
    }).encode()
    req = urllib.request.Request(
        f"https://www.googleapis.com/webmasters/v3/sites/{api_path}/searchAnalytics/query",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        rows = data.get("rows", [])
        if not rows:
            print("  Nenhum dado em nenhum dia — o site ainda não aparece no Google")
        for row in rows:
            print(f"  {row.get('keys')}: cliques={row.get('clicks')} "
                  f"impressoes={row.get('impressions')}")
    except urllib.error.HTTPError as e:
        print(f"  erro {e.code}")


def check_old_domain(token):
    """Domínio antigo para comparação (tem histórico?)."""
    print("\n=== DOMÍNIO ANTIGO (byethost4) — últimos 90 dias ===")
    target = "https://tech-tips.byethost4.com/"
    api_path = urllib.parse.quote(target, safe="")
    body = json.dumps({
        "startDate": "2026-06-21",
        "endDate": "2026-09-19",
        "dimensions": ["date"],
        "rowLimit": 90,
    }).encode()
    req = urllib.request.Request(
        f"https://www.googleapis.com/webmasters/v3/sites/{api_path}/searchAnalytics/query",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        rows = data.get("rows", [])
        if not rows:
            print("  Nenhum dado no domínio antigo")
        total_c = sum(r.get("clicks", 0) for r in rows)
        total_i = sum(r.get("impressions", 0) for r in rows)
        print(f"  total: cliques={total_c} impressoes={total_i} em {len(rows)} dias com dados")
        for row in rows[-10:]:
            print(f"  {row.get('keys')}: cliques={row.get('clicks')} impressoes={row.get('impressions')}")
    except urllib.error.HTTPError as e:
        print(f"  erro {e.code}")


if __name__ == "__main__":
    token, _ = get_access_token("webmasters")
    check_site_live()
    check_sitemaps(token)
    check_daily_impressions(token)
    check_old_domain(token)
