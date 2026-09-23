#!/usr/bin/env python3
"""
GA4 Traffic Fetcher — puxa sessões por origem na Google Analytics Data API
e grava cache em dashboard/data/analytics_source.json.

Uso:
  python scripts/analytics_ga4.py                    # últimos 30 dias
  python scripts/analytics_ga4.py --days 7 --source  # só origem pinterest.com

Depende de:
  - dashboard/google_auth.py (OAuth de usuário — Desktop Client ID)
  - .env: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN,
          GA4_PROPERTY_ID
  - Rodar 1x `python scripts/analytics_ga4.py --auth` p/ gerar o refresh_token
"""
import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "dashboard"))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(PROJECT_ROOT / ".env")

from google_auth import (  # noqa: E402
    get_access_token, GA4_SCOPE,
    auth_status, authorize_interactive, oauth_refresh_token,
)

DATA_DIR = PROJECT_ROOT / "dashboard" / "data"
CACHE_FILE = DATA_DIR / "analytics_source.json"


def _property_id() -> str:
    """Descobre o GA4 property ID (.env ou configuração)."""
    env = os.environ.get("GA4_PROPERTY_ID", "").strip()
    if env:
        return env
    # fallback: ler de analytics_config.json se existir
    cfg_path = DATA_DIR / "analytics_config.json"
    if cfg_path.exists():
        try:
            return str(json.loads(cfg_path.read_text()).get("property_id", ""))
        except Exception:
            pass
    return ""


def list_properties(token: str) -> list:
    """Lista accounts/properties GA4 do usuário (para descobrir o ID).

    A Admin API exige o filtro `parent` na query string (o endpoint aninhado
    /accounts/{a}/properties retorna 404). Usamos o flat `/properties?filter=`.
    """
    import urllib.parse
    import httpx

    def _props(account):
        q = urllib.parse.quote(f"parent:{account}")
        r = httpx.get(
            "https://analyticsadmin.googleapis.com/v1alpha/properties",
            params={"filter": q},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if r.status_code != 200:
            return []
        out = []
        for p in r.json().get("properties", []):
            out.append({
                "property_id": p.get("name", "").split("/")[-1],
                "display_name": p.get("displayName", ""),
                "account": account,
            })
        return out

    resp = httpx.get(
        "https://analyticsadmin.googleapis.com/v1alpha/accounts",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    accounts = resp.json().get("accounts", []) if resp.status_code == 200 else []
    props = []
    for acc in accounts:
        props.extend(_props(acc.get("name")))
    return props


def fetch_by_source(token: str, property_id: str, days: int) -> dict:
    """Chama GA4 Data API: sessões por sessionDefaultChannelGroup+source."""
    import httpx

    end = datetime.now()
    start = end - timedelta(days=days)

    payload = {
        "dateRanges": [
            {"startDate": start.strftime("%Y-%m-%d"), "endDate": end.strftime("%Y-%m-%d")}
        ],
        "dimensions": [
            {"name": "sessionDefaultChannelGroup"},
            {"name": "sessionSource"},
        ],
        "metrics": [{"name": "sessions"}, {"name": "totalUsers"}],
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
        "limit": 25,
    }

    resp = httpx.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}

    data = resp.json()
    rows = data.get("rows", [])
    sources = []
    for r in rows:
        dims = r.get("dimensionValues", [])
        mets = r.get("metricValues", [])
        channel = dims[0]["value"] if dims else ""
        source = dims[1]["value"] if len(dims) > 1 else ""
        sessions = int(mets[0]["value"]) if mets else 0
        users = int(mets[1]["value"]) if len(mets) > 1 else 0
        sources.append({
            "channel": channel, "source": source,
            "sessions": sessions, "users": users,
        })

    return {"success": True, "property_id": property_id,
            "days": days, "sources": sources,
            "fetched_at": datetime.now().isoformat()}


def save_cache(data: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(data, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="GA4 traffic by source")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--source", type=str, default="",
                        help="Filtra e imprime apenas um source (ex: pinterest.com)")
    parser.add_argument("--list-properties", action="store_true")
    parser.add_argument("--auth", action="store_true",
                        help="Fluxo OAuth 1x no navegador: gera e salva o refresh_token no .env")
    parser.add_argument("--status", action="store_true",
                        help="Mostra o estado da autenticação Google")
    args = parser.parse_args()

    if args.status:
        print("Auth:", auth_status())
        if not oauth_refresh_token(verbose=True):
            print("⚠️  Sem access token. Rode: python scripts/analytics_ga4.py --auth")
        return

    if args.auth:
        ok = authorize_interactive()
        if not ok:
            sys.exit(1)
        print("→ Agora rode:")
        print("  python scripts/analytics_ga4.py --list-properties")
        print("  (ou informe GA4_PROPERTY_ID no .env) e depois:")
        print("  python scripts/analytics_ga4.py")
        return

    token = get_access_token(GA4_SCOPE, verbose=True)
    if not token:
        print("❌ Autenticação Google falhou (sem access token).")
        print("   1. Se faltar credencial: .env com GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET")
        print("   2. Gere/regenere o refresh_token: python scripts/analytics_ga4.py --auth")
        sys.exit(1)

    property_id = _property_id()
    if not property_id:
        print("⚠️  GA4_PROPERTY_ID não configurado no .env. Buscando propriedades...")
        props = list_properties(token)
        if not props:
            print("❌ Nenhuma propriedade GA4 encontrada. Ative o Site Kit primeiro.")
            sys.exit(1)
        print("Propriedades encontradas (use uma delas no GA4_PROPERTY_ID):")
        for p in props:
            print(f"   {p['property_id']}  {p['display_name']}")
        property_id = props[0]["property_id"]
        # salvar descoberta
        cfg = {"property_id": property_id}
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "analytics_config.json").write_text(json.dumps(cfg, indent=2))

    result = fetch_by_source(token, property_id, args.days)
    if not result.get("success"):
        print(f"❌ {result.get('error')}")
        sys.exit(1)

    save_cache(result)

    if args.source:
        match = [s for s in result["sources"] if s["source"].lower() == args.source.lower()]
        if match:
            s = match[0]
            print(f"{s['source']}: {s['sessions']} sessões / {s['users']} usuários")
        else:
            print(f"ℹ️  Fonte '{args.source}' sem sessões nos últimos {args.days} dias.")
    else:
        print(f"✅ {result['days']} dias — sessões por origem:")
        for s in result["sources"]:
            print(f"   {s['channel']:<12} {s['source']:<25} {s['sessions']:>5} sessões  {s['users']:>4} usuários")
        print(f"\nCached em {CACHE_FILE.name}")


if __name__ == "__main__":
    main()