#!/usr/bin/env python3
"""Diagnóstico do 403 na API do Dev.to — NUNCA imprime a chave.

Testa a chave com GETs sem efeito colateral:
  1) GET /api/articles/me/published  (endpoint autenticado padrão)
  2) mesmo GET com User-Agent de browser (suspeita de bloqueio de edge)
  3) GET /api/articles/me/drafts
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

key = os.getenv("DEVTO_API_KEY", "")
print(f"chave presente: {bool(key)} | len: {len(key)} | ascii: {key.isascii() if key else '-'} | "
      f"espaços nas bordas: {key != key.strip() if key else '-'}")

if not key:
    sys.exit("DEVTO_API_KEY ausente no .env")


def _get(url: str, headers: dict) -> None:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode(errors="replace")
            print(f"\n✓ {url}\n  status: {r.status} | content-type: {r.headers.get('Content-Type')}")
            print(f"  server: {r.headers.get('Server')} | cf-ray: {r.headers.get('cf-ray')}")
            print(f"  body[:200]: {body[:200]}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"\n✗ {url}\n  status: {e.code}")
        print(f"  headers: server={e.headers.get('Server')} cf-ray={e.headers.get('cf-ray')} "
              f"content-type={e.headers.get('Content-Type')}")
        print(f"  body[{len(body)} chars]: {body[:300] or '(vazio)'}")
    except Exception as e:  # noqa: BLE001
        print(f"\n✗ {url}\n  erro de rede: {type(e).__name__}: {e}")


H_MIN = {"api-key": key, "Accept": "application/json"}
H_UA = {**H_MIN, "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"}

print("\n── 1) api-key puro (urllib UA default) ──")
_get("https://dev.to/api/articles/me/published?per_page=1", H_MIN)

print("\n── 2) com User-Agent de browser ──")
_get("https://dev.to/api/articles/me/published?per_page=1", H_UA)

print("\n── 3) drafts com UA de browser ──")
_get("https://dev.to/api/articles/me/drafts?per_page=1", H_UA)
