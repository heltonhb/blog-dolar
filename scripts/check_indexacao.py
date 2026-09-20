#!/usr/bin/env python3
"""Avalia indexação no Google via Search Console API (OAuth de usuário)."""
import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error


def _env(key):
    """Lê variável do .env (arquivo), com fallback pro ambiente."""
    for line in open(".env"):
        line = line.strip()
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return os.environ.get(key, "")


def get_access_token(scope):
    client_id = _env("GOOGLE_CLIENT_ID")
    client_secret = _env("GOOGLE_CLIENT_SECRET")
    refresh = _env("GOOGLE_REFRESH_TOKEN")
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh,
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
    return d["access_token"], d.get("scope", "")


def api_get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}"), e.code


def main():
    token, scope = get_access_token("webmasters")
    print(f"[auth] token obtido, scope: {scope}")

    # 1. Listar sites do Search Console
    sites, code = api_get("https://www.googleapis.com/webmasters/v3/sites", token)
    if code != 200:
        print(f"[erro] sites: {code} {sites}")
        sys.exit(1)
    print("[sites Search Console]")
    for s in sites.get("siteEntry", []):
        print(f"  - {s.get('siteUrl')}  (permissao: {s.get('permission')})")

    # 2. Métricas de search analytics (90 dias) — por query e por página
    site_entry = {s.get("siteUrl"): s for s in sites.get("siteEntry", [])}
    target = "https://tech-tips.ct.ws/"
    if target not in site_entry:
        print("[aviso] tech-tips.ct.ws não verificado no Search Console")
    print(f"[alvo] {target}")
    api_path = urllib.parse.quote(target, safe="")

    for dim in ("query", "page"):
        body = json.dumps({
            "startDate": "2026-06-21",
            "endDate": "2026-09-19",
            "dimensions": [dim],
            "rowLimit": 50,
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
            print(f"\n[por {dim}] {len(rows)} resultados nos últimos 90 dias")
            for row in rows[:15]:
                k = row.get("keys", ["?"])[0]
                print(f"  {k[:80]}: cliques={row.get('clicks')} impressoes={row.get('impressions')} pos={row.get('position'):.1f}")
            if dim == "page":
                indexed_pages = [r.get("keys", ["?"])[0] for r in rows]
                with open("scripts/indexacao_paginas.json", "w") as f:
                    json.dump(rows, f, indent=2)
        except urllib.error.HTTPError as e:
            print(f"[erro] analytics por {dim}: {e.code}")


if __name__ == "__main__":
    main()
