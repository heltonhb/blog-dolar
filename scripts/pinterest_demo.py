#!/usr/bin/env python3
"""Demonstração end-to-end da integração Pinterest (para o vídeo de review).

Mostra, em sequência, o que o app faz:
  1. autentica com o access token (OAuth)
  2. lê a conta e lista os boards
  3. garante um board de demonstração
  4. cria um pin com imagem, link e descrição

Uso (trial access, padrão):
    python scripts/pinterest_demo.py --pause 2

Uso (produção, após Standard access):
    PINTEREST_API_BASE=https://api.pinterest.com/v5 python scripts/pinterest_demo.py

O `--dry-run` mostra os passos sem criar board/pin.
"""
import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

SANDBOX = "https://api-sandbox.pinterest.com/v5"
PRODUCTION = "https://api.pinterest.com/v5"

DEMO_BOARD = "Tech Tips Daily - Demo"
DEMO_TITLE = "Smart Home Security Gadgets You Need in 2026"
DEMO_DESC = (
    "Practical smart home security gadgets that are worth it in 2026: "
    "cameras, sensors and automations. Full guide on the blog. #smarthome #tech"
)
DEMO_LINK = os.environ.get("SITE_URL", "https://techtips.dpdns.org")
DEMO_IMAGE = os.environ.get(
    "PINTEREST_DEMO_IMAGE",
    "https://techtips.dpdns.org/wp-content/uploads/2026/10/"
    "pin-ssd-vs-hdd-storage-difference-2.png",
)


def base() -> str:
    return os.environ.get("PINTEREST_API_BASE", SANDBOX).rstrip("/")


def step(n: int, text: str) -> None:
    print()
    print(f"── Step {n} ─────────────────────────────────────────────")
    print(f"   {text}")
    print()


def call(method: str, path: str, token: str, **kwargs):
    import httpx

    return httpx.request(
        method,
        f"{base()}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
        **kwargs,
    )


def find_or_create_board(token: str, dry_run: bool) -> str:
    resp = call("GET", "/boards", token, params={"page_size": 100})
    print(f"GET /boards -> HTTP {resp.status_code}")
    boards = resp.json().get("items", []) if resp.status_code == 200 else []
    for b in boards:
        print(f"   • {b.get('name')} (id: {b.get('id')})")
        if b.get("name") == DEMO_BOARD:
            return b["id"]

    if dry_run:
        print(f"   [dry-run] criaria o board '{DEMO_BOARD}'")
        return "DRY_RUN_BOARD_ID"

    resp = call(
        "POST",
        "/boards",
        token,
        json={"name": DEMO_BOARD, "description": "Pins created by the Tech Tips Daily automation."},
    )
    print(f"POST /boards -> HTTP {resp.status_code}")
    if resp.status_code not in (200, 201):
        print(f"   {resp.text[:300]}")
        return ""
    board_id = resp.json().get("id", "")
    print(f"   board criado: {board_id}")
    return board_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Pinterest end-to-end demo")
    parser.add_argument("--dry-run", action="store_true", help="Não cria board/pin")
    parser.add_argument("--pause", type=float, default=0,
                        help="Segundos de pausa entre passos (útil na gravação)")
    parser.add_argument("--image-url", default=DEMO_IMAGE)
    args = parser.parse_args()

    def hold() -> None:
        if args.pause:
            time.sleep(args.pause)

    token = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
    if not token:
        print("❌ PINTEREST_ACCESS_TOKEN ausente no .env")
        return 1

    print("Pinterest API — end-to-end demo")
    print(f"API base: {base()}")

    step(1, "Authenticate the app with the Pinterest access token (OAuth 2.0)")
    resp = call("GET", "/user_account", token)
    print(f"GET /user_account -> HTTP {resp.status_code}")
    if resp.status_code != 200:
        print(f"   {resp.text[:300]}")
        print("\nDica: em trial access use a API sandbox (padrão deste script).")
        return 1
    account = resp.json()
    print(f"   username: {account.get('username')}")
    print(f"   business: {account.get('business_name')}")
    print(f"   website:  {account.get('website_url')}")
    hold()

    step(2, "List the boards available to the app")
    board_id = find_or_create_board(token, args.dry_run)
    if not board_id:
        return 1
    hold()

    step(3, "Create a Pin with image, destination link and description")
    payload = {
        "board_id": board_id,
        "title": DEMO_TITLE[:100],
        "description": DEMO_DESC[:500],
        "link": DEMO_LINK,
        "media_source": {"source_type": "image_url", "url": args.image_url},
    }
    print("POST /pins")
    print(json.dumps({k: (v[:60] + "…" if isinstance(v, str) and len(v) > 60 else v)
                      for k, v in payload.items()}, indent=2, ensure_ascii=False))
    if args.dry_run:
        print("   [dry-run] pin não criado")
    else:
        resp = call("POST", "/pins", token, json=payload)
        print(f"   HTTP {resp.status_code}")
        print(f"   {resp.text[:400]}")
        if resp.status_code not in (200, 201):
            return 1
        pin_id = resp.json().get("id", "")
        print(f"\n✅ Pin criado: {pin_id}")
        print(f"   https://www.pinterest.com/pin/{pin_id}/")

    print("\nDemo concluída.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
