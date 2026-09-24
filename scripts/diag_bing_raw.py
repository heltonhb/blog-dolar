#!/usr/bin/env python3
"""Confirma a resposta CRUA da API do Bing p/ o site (GetQueryStats)."""
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

key = os.environ["BING_API_KEY"]
site = os.environ.get("SITE_URL", "https://tech-tips.ct.ws")

r = httpx.get(
    "https://ssl.bing.com/webmaster/api.svc/json/GetQueryStats",
    params={"siteUrl": site, "apikey": key},
    timeout=25,
)
print(f"HTTP {r.status_code} | content-type: {r.headers.get('content-type')}")
print(f"corpo ({len(r.text)} chars):")
print(r.text[:500])
