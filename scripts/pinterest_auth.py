#!/usr/bin/env python3
"""Pinterest OAuth — gera a URL de autorização e troca o `code` por tokens.

Uso:
    python scripts/pinterest_auth.py
    python scripts/pinterest_auth.py --code SEU_CODE --redirect-uri https://localhost

O access token do Pinterest dura 30 dias; o refresh token, 1 ano. Guardamos os
dois no .env para que o publisher renove o access token sozinho.
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(Path(__file__).parent))
from pinterest_setup import (  # noqa: E402
    authorize_url,
    exchange_code,
    list_boards,
    save_token_to_env,
    test_connection,
)

PRODUCTION_BASE = "https://api.pinterest.com/v5"


def main() -> int:
    parser = argparse.ArgumentParser(description="Pinterest OAuth helper")
    parser.add_argument("--code", help="Código recebido no redirect_uri")
    parser.add_argument("--redirect-uri", default="https://localhost",
                        help="redirect_uri registrado no app Pinterest")
    parser.add_argument("--scopes", default="",
                        help="Escopos separados por vírgula")
    parser.add_argument("--sandbox", action="store_true",
                        help="Valida o token no sandbox depois de salvar")
    args = parser.parse_args()

    client_id = os.environ.get("PINTEREST_CLIENT_ID", "")
    client_secret = os.environ.get("PINTEREST_CLIENT_SECRET", "")
    if not (client_id and client_secret):
        print("❌ Configure PINTEREST_CLIENT_ID e PINTEREST_CLIENT_SECRET no .env")
        return 1

    if not args.code:
        print("Abra esta URL, autorize o app e copie o `code` do redirect:")
        print()
        print(authorize_url(args.redirect_uri, args.scopes))
        print()
        print("Depois rode:")
        print(f"  python scripts/pinterest_auth.py --code SEU_CODE "
              f"--redirect-uri {args.redirect_uri}")
        return 0

    # A troca do code acontece sempre na API de produção.
    os.environ["PINTEREST_API_BASE"] = PRODUCTION_BASE
    data = exchange_code(args.code, args.redirect_uri)
    if not data.get("access_token"):
        return 1

    save_token_to_env(data["access_token"], data.get("refresh_token", ""))

    if args.sandbox:
        os.environ["PINTEREST_API_BASE"] = "https://api-sandbox.pinterest.com/v5"
    if test_connection(data["access_token"]):
        boards = list_boards(data["access_token"])
        if boards:
            print("\nBoard ID sugerido para o .env:")
            print(f"PINTEREST_BOARD_ID={boards[0].get('id', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
