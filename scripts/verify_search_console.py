#!/usr/bin/env python3
"""Verifica se as credenciais do Google Search Console estão funcionando."""
import json, sys
from pathlib import Path

def check_credentials():
    paths = [
        Path(__file__).parent.parent / "google-search-console.json",
        Path(__file__).parent.parent / "dashboard" / "data" / "google-search-console.json",
    ]
    for p in paths:
        if p.exists():
            with open(p) as f:
                creds = json.load(f)
            print(f"✅ Arquivo encontrado: {p}")
            print(f"   Client email: {creds.get('client_email', 'N/A')}")
            print(f"   Project ID: {creds.get('project_id', 'N/A')}")
            return creds
    print("❌ Arquivo google-search-console.json não encontrado!")
    print("   Siga as instruções em docs/SETUP_SEARCH_CONSOLE.md")
    return None

def test_token(creds):
    import time, base64, httpx
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    now = int(time.time())
    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({
        "iss": creds["client_email"],
        "scope": "https://www.googleapis.com/auth/webmasters https://www.googleapis.com/auth/indexing",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }).encode()).rstrip(b"=").decode()

    private_key = load_pem_private_key(creds["private_key"].encode(), password=None)
    signature = private_key.sign(f"{header}.{payload}".encode(), padding.PKCS1v15(), hashes.SHA256())
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    jwt_token = f"{header}.{payload}.{signature_b64}"

    resp = httpx.post("https://oauth2.googleapis.com/token", data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt_token,
    }, timeout=10)

    if resp.status_code == 200:
        token = resp.json().get("access_token")
        print(f"✅ Token obtido com sucesso!")
        print(f"   Token: {token[:20]}...")
        return token
    else:
        print(f"❌ Erro ao obter token: {resp.status_code}")
        print(f"   {resp.text[:200]}")
        return None

if __name__ == "__main__":
    print("=" * 50)
    print("  Google Search Console — Verificação")
    print("=" * 50)
    print()

    creds = check_credentials()
    if not creds:
        sys.exit(1)

    print()
    token = test_token(creds)
    if token:
        print("\n✅ Tudo pronto! Rodar: python scripts/index_search_console.py")
    else:
        print("\n❌ Verifique as credenciais e permissões da Service Account")
