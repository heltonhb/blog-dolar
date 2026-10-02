#!/usr/bin/env python3
"""Smoke test do dashboard com sessão autenticada (sem passar pelo rate-limit)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from dashboard import create_app  # noqa: E402

app = create_app()
app.config["TESTING"] = True
client = app.test_client()

CSRF = "smoke-csrf"

with client.session_transaction() as sess:
    sess["authenticated"] = True
    sess["_csrf_token"] = CSRF

# 1) página /traffic renderiza com o card do Bing
r = client.get("/traffic")
ok_page = r.status_code == 200 and b"bing-impressions" in r.data and b"refreshBing" in r.data
print(f"/traffic: {r.status_code} | card bing presente: {ok_page}")

# 2) API do bing responde JSON estruturado, com ou sem dados em cache
r = client.get("/api/traffic/bing")
data = r.get_json()
ok_api = r.status_code == 200 and isinstance(data, dict) and "success" in data
print(f"/api/traffic/bing: {r.status_code} | resposta estruturada: {ok_api} | success={data.get('success')}")

# 3) refresh exige o token CSRF (o header é enviado como o layout.html faz)
r = client.post("/api/traffic/bing/refresh", headers={"X-CSRF-Token": CSRF})
data = r.get_json()
# Sucesso (200) ou erro tratado por falta de credencial (400) são aceitáveis;
# o que não pode passar é um 500 sem tratamento.
ok_refresh = r.status_code in (200, 400, 503) and isinstance(data, dict)
print(f"/api/traffic/bing/refresh: {r.status_code} | resposta tratada: {ok_refresh}")

assert ok_page and ok_api and ok_refresh, "smoke falhou"
print("\n✅ smoke completo: página renderiza, APIs respondem, refresh autenticado")
