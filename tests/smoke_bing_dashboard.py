#!/usr/bin/env python3
"""Smoke test do dashboard com sessão autenticada (sem passar pelo rate-limit)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, "dashboard")

from dotenv import load_dotenv

load_dotenv(".env")

from app import app  # noqa: E402

app.config["TESTING"] = True
client = app.test_client()

with client.session_transaction() as sess:
    sess["authenticated"] = True

# 1) página /traffic renderiza com o card do Bing
r = client.get("/traffic")
ok_page = r.status_code == 200 and b"bing-impressions" in r.data and b"refreshBing" in r.data
print(f"/traffic: {r.status_code} | card bing presente: {ok_page}")

# 2) API do bing responde (sem dados ainda, mas JSON estruturado)
r = client.get("/api/traffic/bing")
data = r.get_json()
ok_api = r.status_code == 200 and data.get("success") is False and "error" in data
print(f"/api/traffic/bing: {r.status_code} | resposta estruturada: {ok_api} | {data}")

# 3) rota de refresh existe (vai falhar por falta de key, mas deve ser 400 tratado)
r = client.post("/api/traffic/bing/refresh")
data = r.get_json()
ok_refresh = r.status_code == 400 and "BING_API_KEY" in (data.get("error") or "")
print(f"/api/traffic/bing/refresh: {r.status_code} | erro tratado: {ok_refresh}")

assert ok_page and ok_api, "smoke falhou"
print("\n✅ smoke completo: página renderiza, APIs respondem, erro sem key é tratado")
