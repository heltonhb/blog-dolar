#!/usr/bin/env python3
"""Autenticação Google compartilhada.

Reutilizada por GA4 Analytics (scripts/analytics_ga4.py) e pelo
Search Console (scripts/index_search_console.py).

Método principal (from 2026-09-16): OAuth de usuário — Desktop Client ID.
   A política do Google Cloud (`iam.disableServiceAccountKeyCreation`) bloqueia o
   download de chave de service account no projeto blog-dollar-508211, então
   usamos OAuth de usuário: `client_id` + `client_secret` + `refresh_token`.

   Variáveis (no .env):
     GOOGLE_CLIENT_ID=<seu Desktop Client ID>
     GOOGLE_CLIENT_SECRET=<seu Client Secret>
     GOOGLE_REFRESH_TOKEN=<gerado 1x pelo fluxo de autorização>

   Gerar o refresh_token uma única vez:
     python scripts/analytics_ga4.py --auth

Fallback (só p/ compatibilidade): service account JWT pelo arquivo
   `google-search-console.json` na raiz — mantido para não quebrar fluxos
   antigos, mas NÃO conseguirá ser criado por causa da política citada.

Escopos:
  - GA4:            analytics.readonly
  - Search Console: webmasters, indexing
"""
import base64
import json
import os
import time
import webbrowser
import urllib.parse
import http.server
import socketserver
from pathlib import Path

CREDENTIAL_FILENAME = "google-search-console.json"

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

GA4_SCOPE = ["https://www.googleapis.com/auth/analytics.readonly"]
# Escopo de escrita (criar conta/propriedade GA4 via Admin API)
GA4_WRITE_SCOPE = ["https://www.googleapis.com/auth/analytics.edit"]
SEARCH_CONSOLE_SCOPE = [
    "https://www.googleapis.com/auth/webmasters",
    "https://www.googleapis.com/auth/indexing",
]
# Escopo usado no fluxo interativo (cobre criar+ler GA4 e Search Console).
_ALL_SCOPES = list(dict.fromkeys(
    GA4_SCOPE + GA4_WRITE_SCOPE + SEARCH_CONSOLE_SCOPE
))

_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
_TOKEN_URI = "https://oauth2.googleapis.com/token"
_LOOPBACK_PORT = 8181
_REDIRECT_URI = f"http://localhost:{_LOOPBACK_PORT}/"


# --------------------------------------------------------------------------- #
# Leitura / escrita segura do .env
# --------------------------------------------------------------------------- #
def _load_dotenv() -> dict:
    d = {}
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                d[k.strip()] = v.strip()
    return d


def _env(key: str) -> str:
    return (os.environ.get(key) or "").strip() or _load_dotenv().get(key, "").strip()


def _write_env(key: str, value: str):
    """Escreve/atualiza uma chave no .env preservando o resto do arquivo."""
    lines = _ENV_PATH.read_text().splitlines() if _ENV_PATH.exists() else []
    out, found = [], False
    for line in lines:
        if line.strip().startswith(key + "="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    _ENV_PATH.write_text("\n".join(out) + "\n")


def oauth_configured() -> bool:
    return bool(_env("GOOGLE_CLIENT_ID") and _env("GOOGLE_CLIENT_SECRET")
                and _env("GOOGLE_REFRESH_TOKEN"))


# --------------------------------------------------------------------------- #
# OAuth de usuário (Desktop Client ID) — fluxo principal
# --------------------------------------------------------------------------- #
def oauth_refresh_token() -> str:
    """Troca o GOOGLE_REFRESH_TOKEN por um access_token. '' se falhar."""
    if not oauth_configured():
        return ""
    import httpx
    resp = httpx.post(_TOKEN_URI, data={
        "client_id": _env("GOOGLE_CLIENT_ID"),
        "client_secret": _env("GOOGLE_CLIENT_SECRET"),
        "refresh_token": _env("GOOGLE_REFRESH_TOKEN"),
        "grant_type": "refresh_token",
    }, timeout=15)
    if resp.status_code == 200:
        return resp.json().get("access_token", "")
    return ""


def authorize_interactive() -> bool:
    """Fluxo de autorização 1x no navegador (loopback). Salva o refresh_token no .env."""
    client_id = _env("GOOGLE_CLIENT_ID")
    client_secret = _env("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("❌ Configure GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no .env primeiro.")
        return False

    params = {
        "client_id": client_id,
        "redirect_uri": _REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(_ALL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = _AUTH_URI + "?" + urllib.parse.urlencode(params)
    print("1. Autorize no navegador (aberto automaticamente). Se não abrir, cole:")
    print("   " + auth_url)
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    code_holder: dict = {"code": ""}

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            q = urllib.parse.parse_qs(parsed.query)
            if "code" in q:
                code_holder["code"] = q["code"][0]
            body = b"<h3>Autorizado! Pode fechar esta aba e voltar ao terminal.</h3>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # silencia log
            pass

    print(f"2. Aguardando o redirect para {_REDIRECT_URI} (timeout 5 min)...")
    with socketserver.TCPServer(("", _LOOPBACK_PORT), _Handler) as httpd:
        httpd.timeout = 300
        deadline = time.time() + 300
        while not code_holder["code"] and time.time() < deadline:
            httpd.handle_request()
        httpd.server_close()

    if not code_holder["code"]:
        print("❌ Timeout ou autorização cancelada.")
        return False

    import httpx
    resp = httpx.post(_TOKEN_URI, data={
        "code": code_holder["code"],
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": _REDIRECT_URI,
        "grant_type": "authorization_code",
    }, timeout=15)
    tok = resp.json()
    refresh = tok.get("refresh_token")
    if not refresh:
        print("❌ Não veio refresh_token:", resp.text[:400])
        return False

    _write_env("GOOGLE_REFRESH_TOKEN", refresh)
    print("✅ refresh_token gerado e salvo no .env (GOOGLE_REFRESH_TOKEN).")
    return True


# --------------------------------------------------------------------------- #
# Fallback: service account JWT (fluxo antigo, mantido p/ compatibilidade)
# --------------------------------------------------------------------------- #
def find_credentials():
    """Procura o arquivo de credencial service-account em locais conhecidos."""
    project_root = Path(__file__).resolve().parent.parent
    candidates = [
        project_root / CREDENTIAL_FILENAME,
        project_root / "dashboard" / "data" / CREDENTIAL_FILENAME,
        Path.home() / "blog-dolar" / CREDENTIAL_FILENAME,
    ]
    for path in candidates:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    return None


def _jwt_access_token(creds: dict, scopes: list) -> str:
    """Monta e assina um JWT para o fluxo service-account."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    now = int(time.time())
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({
        "iss": creds["client_email"],
        "scope": " ".join(scopes),
        "aud": _TOKEN_URI,
        "iat": now,
        "exp": now + 3600,
    }).encode()).rstrip(b"=").decode()

    private_key = load_pem_private_key(creds["private_key"].encode(), password=None)
    signature = private_key.sign(
        f"{header}.{payload}".encode(), padding.PKCS1v15(), hashes.SHA256()
    )
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{header}.{payload}.{signature_b64}"


def get_access_token(scopes: list) -> str:
    """Retorna um access token Google ('' se não houver credencial).

    Prioridade: (1) OAuth de usuário via refresh_token no .env;
                (2) service account JWT (google-search-console.json).
    """
    import httpx

    # 1) OAuth de usuário — método atual
    token = oauth_refresh_token()
    if token:
        return token

    # 2) Fallback: service account JWT (fluxo antigo)
    creds = find_credentials()
    if not creds:
        return ""
    jwt = _jwt_access_token(creds, scopes)
    resp = httpx.post(
        _TOKEN_URI,
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
              "assertion": jwt},
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json().get("access_token", "")
    return ""


def auth_status() -> str:
    """Descrição legível do estado de autenticação para o dashboard/logs."""
    if oauth_configured():
        return "oauth (refresh_token no .env)"
    if find_credentials():
        return "service-account JWT (fallback)"
    return "sem credencial Google"