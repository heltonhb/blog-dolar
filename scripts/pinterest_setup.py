#!/usr/bin/env python3
"""Pinterest Setup — Verifica conexão, lista boards, e configura automação."""
import json, os, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DEFAULT_API_BASE = "https://api.pinterest.com/v5"
SANDBOX_API_BASE = "https://api-sandbox.pinterest.com/v5"


def api_base() -> str:
    """Base da API. Tokens de trial (app sem standard access) só funcionam no sandbox."""
    return os.environ.get("PINTEREST_API_BASE", DEFAULT_API_BASE).rstrip("/")


def authorize_url(redirect_uri: str, scopes: str = "") -> str:
    """Monta a URL de autorização OAuth (Authorization Code grant)."""
    import urllib.parse

    client_id = os.environ.get("PINTEREST_CLIENT_ID", "")
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scopes or "boards:read,pins:read,pins:write,board_pins:write",
    }
    return "https://www.pinterest.com/oauth/?" + urllib.parse.urlencode(params)


def exchange_code(code: str, redirect_uri: str) -> dict:
    """Troca o `code` do OAuth por access_token + refresh_token."""
    import base64

    import httpx

    client_id = os.environ.get("PINTEREST_CLIENT_ID", "")
    client_secret = os.environ.get("PINTEREST_CLIENT_SECRET", "")
    if not (client_id and client_secret):
        print("❌ PINTEREST_CLIENT_ID/PINTEREST_CLIENT_SECRET ausentes no .env")
        return {}
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = httpx.post(
        f"{api_base()}/oauth/token",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=15,
    )
    if resp.status_code == 200:
        data = resp.json()
        print("✅ Código trocado por token com sucesso!")
        print(f"   Escopos: {data.get('scope', '?')}")
        print(f"   Expira em: {data.get('expires_in', 0)} segundos")
        return data
    print(f"❌ Erro ao trocar o código: {resp.status_code}")
    print(f"   {resp.text[:300]}")
    return {}


def test_connection(token: str) -> bool:
    """Testa conexão com Pinterest API."""
    import httpx
    resp = httpx.get(
        f"{api_base()}/user_account",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Conectado como: {data.get('username', '?')}")
        print(f"   Nome: {data.get('first_name', '')} {data.get('last_name', '')}")
        print(f"   Profile: {data.get('profile_url', '')}")
        return True
    else:
        print(f"❌ Autenticação falhou: {resp.status_code}")
        print(f"   {resp.text[:200]}")
        return False

def list_boards(token: str) -> list:
    """Lista boards do usuário."""
    import httpx
    resp = httpx.get(
        f"{api_base()}/boards",
        headers={"Authorization": f"Bearer {token}"},
        params={"page_size": 25},
        timeout=15,
    )
    if resp.status_code == 200:
        boards = resp.json().get("items", [])
        print(f"\n📋 Boards encontrados: {len(boards)}")
        for i, b in enumerate(boards, 1):
            print(f"  {i}. {b.get('name')} (pins: {b.get('pin_count', 0)}, id: {b.get('id', '')})")
        return boards
    else:
        print(f"\n❌ Erro ao listar boards: {resp.status_code}")
        return []

def create_pin(token: str, board_id: str, title: str, description: str,
               link: str, image_url: str) -> dict:
    """Cria um pin no Pinterest."""
    import httpx
    payload = {
        "board_id": board_id,
        "title": title[:100],
        "description": description[:500],
        "link": link,
        "media_source": {"source_type": "image_url", "url": image_url},
    }
    resp = httpx.post(
        f"{api_base()}/pins",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code in (200, 201):
        pin = resp.json()
        print(f"  ✅ Pin criado: {pin.get('id')}")
        return {"success": True, "pin_id": pin.get("id")}
    else:
        print(f"  ❌ Erro: {resp.status_code} - {resp.text[:200]}")
        return {"success": False, "error": resp.text[:200]}

def refresh_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    """Renova access token usando refresh token."""
    import httpx
    import base64
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = httpx.post(
        f"{api_base()}/oauth/token",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=15,
    )
    if resp.status_code == 200:
        data = resp.json()
        print("✅ Token renovado com sucesso!")
        print(f"   Novo access_token: {data.get('access_token', '')[:20]}...")
        print(f"   Expira em: {data.get('expires_in', 0)} segundos")
        return data
    else:
        print(f"❌ Erro ao renovar token: {resp.status_code}")
        print(f"   {resp.text[:200]}")
        return {}

def save_token_to_env(new_token: str, refresh_token: str = None):
    """Salva token no arquivo .env."""
    env_path = Path(__file__).parent.parent / ".env"
    lines = env_path.read_text().splitlines()
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith("PINTEREST_ACCESS_TOKEN="):
            new_lines.append(f"PINTEREST_ACCESS_TOKEN={new_token}")
            updated = True
        elif line.startswith("PINTEREST_REFRESH_TOKEN=") and refresh_token:
            new_lines.append(f"PINTEREST_REFRESH_TOKEN={refresh_token}")
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"PINTEREST_ACCESS_TOKEN={new_token}")
    if refresh_token:
        has_refresh = any(l.startswith("PINTEREST_REFRESH_TOKEN=") for l in new_lines)
        if not has_refresh:
            new_lines.append(f"PINTEREST_REFRESH_TOKEN={refresh_token}")
    env_path.write_text("\n".join(new_lines) + "\n")
    print("✅ Token salvo no .env")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pinterest setup e diagnóstico")
    parser.add_argument("--sandbox", action="store_true",
                        help="Usa api-sandbox.pinterest.com (necessário no trial access)")
    parser.add_argument("--redirect-uri", default="https://localhost",
                        help="redirect_uri registrado no app (para gerar a URL OAuth)")
    args = parser.parse_args()

    if args.sandbox:
        os.environ["PINTEREST_API_BASE"] = SANDBOX_API_BASE
    print("=" * 55)
    print("  Pinterest Setup — Blog em Dolar")
    print(f"  API: {api_base()}")
    print("=" * 55)
    print()

    token = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
    if not token:
        print("❌ PINTEREST_ACCESS_TOKEN não configurado no .env")
        print("   Siga: docs/SETUP_PINTEREST.md")
        sys.exit(1)

    if test_connection(token):
        boards = list_boards(token)
        if boards:
            print("\nPara usar um board, adicione no .env:")
            print(f"PINTEREST_BOARD_ID={boards[0].get('id', '')}")
    else:
        print("\nToken rejeitado neste ambiente. Opções:")
        print("  1. Se o app está em trial access, rode com --sandbox")
        print("  2. Gere um token novo via Authorization Code:")
        print(f"     {authorize_url(args.redirect_uri)}")
        print("     Depois: python scripts/pinterest_auth.py --redirect-uri "
              f"{args.redirect_uri} --code SEU_CODE")
        print("  3. Renove com refresh token: python scripts/pinterest_setup.py")
