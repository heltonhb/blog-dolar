#!/usr/bin/env python3
"""
analytics_bing.py — Puxa impressões/cliques do Bing Webmaster Tools API
e grava cache em dashboard/data/bing_stats.json (mesmo padrão do GA4).

Uso:
  python scripts/analytics_bing.py                  # últimos 30 dias
  python scripts/analytics_bing.py --days 7

Depende de:
  - .env: BING_API_KEY (gerada no painel: Settings → Preferences → API access)
  - .env: SITE_URL (default https://tech-tips.ct.ws)

API: https://ssl.bing.com/webmaster/api.svc/json/GetQueryStats
Datas vêm em /Date(ms)/ — convertidas para ISO.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "dashboard" / "data"
CACHE_FILE = DATA_DIR / "bing_stats.json"

API = "https://ssl.bing.com/webmaster/api.svc/json"


def _ms_para_iso(data_bing: str) -> str:
    """/Date(1399100400000-0700)/ → '2024-05-03' (data local do timestamp)."""
    m = re.match(r"/Date\((\d+)", data_bing or "")
    if not m:
        return ""
    return datetime.fromtimestamp(int(m.group(1)) / 1000).strftime("%Y-%m-%d")


def _fetch(endpoint: str, api_key: str, site_url: str, timeout: int = 25) -> dict | None:
    """Chama um endpoint do Bing e devolve o campo 'd' (lista) ou None."""
    r = httpx.get(
        f"{API}/{endpoint}",
        params={"siteUrl": site_url, "apikey": api_key},
        timeout=timeout,
    )
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    data = r.json()
    if isinstance(data, dict) and data.get("ErrorCode", 0) != 0:
        raise RuntimeError(f"Bing ErrorCode {data.get('ErrorCode')}: {data.get('ErrorMessage', '')[:200]}")
    return data.get("d")


def fetch_bing_stats(days: int = 30) -> dict:
    """Impressões/cliques por dia + top queries, limitados a `days`."""
    api_key = os.environ.get("BING_API_KEY", "").strip()
    site_url = os.environ.get("SITE_URL", "https://tech-tips.ct.ws").strip()
    if not api_key:
        return {"success": False, "error": "BING_API_KEY ausente no .env "
                "(gere em Bing Webmaster Tools → Settings → Preferences → API access)"}

    # Totais por dia (agrega todas as queries)
    diario = _fetch("GetQueryStats", api_key, site_url)
    if not isinstance(diario, list):
        return {"success": False, "error": "resposta inesperada da API do Bing"}

    limite = datetime.now().timestamp() - days * 86400
    por_dia: dict[str, dict] = {}
    queries: dict[str, dict] = {}
    for linha in diario:
        data_iso = _ms_para_iso(linha.get("Date", ""))
        if not data_iso:
            continue
        # GetQueryStats devolve 1 linha por query por dia — agrega por dia
        dia = por_dia.setdefault(data_iso, {"impressions": 0, "clicks": 0})
        dia["impressions"] += int(linha.get("Impressions", 0))
        dia["clicks"] += int(linha.get("Clicks", 0))
        q = linha.get("Query", "")
        if q:
            qq = queries.setdefault(q, {"query": q, "impressions": 0, "clicks": 0})
            qq["impressions"] += int(linha.get("Impressions", 0))
            qq["clicks"] += int(linha.get("Clicks", 0))

    # mantém só os últimos N dias
    dias_validos = {d: v for d, v in por_dia.items()
                    if datetime.strptime(d, "%Y-%m-%d").timestamp() >= limite}
    top_queries = sorted(queries.values(), key=lambda x: -x["impressions"])[:15]

    total_imp = sum(v["impressions"] for v in dias_validos.values())
    total_clk = sum(v["clicks"] for v in dias_validos.values())

    return {
        "success": True,
        "site_url": site_url,
        "days": days,
        "totals": {
            "impressions": total_imp,
            "clicks": total_clk,
            "ctr": round(total_clk / total_imp * 100, 2) if total_imp else 0.0,
        },
        "by_day": sorted(
            [{"date": d, **v} for d, v in dias_validos.items()],
            key=lambda x: x["date"],
        ),
        "top_queries": top_queries,
        "fetched_at": datetime.now().isoformat(),
    }


def save_cache(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(data, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Bing Webmaster stats")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()

    result = fetch_bing_stats(args.days)
    if not result.get("success"):
        print(f"❌ {result.get('error')}")
        sys.exit(1)

    save_cache(result)
    t = result["totals"]
    print(f"✅ Bing — últimos {result['days']} dias:")
    print(f"   Impressões: {t['impressions']} | Cliques: {t['clicks']} | CTR: {t['ctr']}%")
    if result["by_day"]:
        print(f"   Dias com dados: {len(result['by_day'])} (último: {result['by_day'][-1]['date']})")
    if result["top_queries"]:
        print("   Top queries:")
        for q in result["top_queries"][:5]:
            print(f"     {q['impressions']:>5} imp / {q['clicks']:>3} clk — {q['query'][:50]}")
    print(f"\nCached em {CACHE_FILE.name}")


if __name__ == "__main__":
    main()
