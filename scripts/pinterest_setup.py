#!/usr/bin/env python3
"""Pinterest Setup — Verifica conexão, lista boards, e configura automação."""
import json, os, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

def test_connection(token: str) -> bool:
    """Testa conexão com Pinterest API."""
    import httpx
    resp = httpx.get(
        "https://api.pinterest.com/v5/user_account",
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
        "https://api.pinterest.com/v5/boards",
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
        "image_source_url": image_url,
    }
    resp = httpx.post(
        "https://api.pinterest.com/v5/pins",
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
        "https://api.pinterest.com/v5/oauth/token",
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
    print("=" * 50)
    print("  Pinterest Setup — Blog em Dolar")
    print("=" * 50)
    print()

    token = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
    if not token:
        print("❌ PINTEREST_ACCESS_TOKEN não configurado no .env")
        print("   Siga: docs/SETUP_PINTEREST.md")
        sys.exit(1)

    if test_connection(token):
        boards = list_boards(token)
        if boards:
            print(f"\nPara usar um board, adicione no .env:")
            print(f"PINTEREST_BOARD_ID={boards[0].get('id', '')}")
    else:
        print("\nToken expirado. Opções:")
        print("  1. Regenerar token: docs/SETUP_PINTEREST.md")
        print("  2. Renovar com refresh token:")
        print("     python scripts/pinterest_setup.py refresh")
