#!/usr/bin/env python3
"""Google Search Console Indexer - Solicita indexação de URLs automaticamente."""
import json
import os
import sys
from pathlib import Path

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

def get_credentials():
    """Load Google service account credentials."""
    # Try multiple locations for the credentials file
    possible_paths = [
        Path(__file__).parent.parent / "google-search-console.json",
        Path(__file__).parent.parent / "dashboard" / "data" / "google-search-console.json",
        Path.home() / "blog-dolar" / "google-search-console.json",
    ]
    
    for path in possible_paths:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    
    return None

def get_access_token():
    """Get OAuth2 access token using service account."""
    import httpx
    
    creds = get_credentials()
    if not creds:
        print("❌ Arquivo de credenciais não encontrado!")
        print("   Coloque google-search-console.json na raiz do projeto")
        return None
    
    # Create JWT
    import time
    import base64
    
    now = int(time.time())
    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({
        "iss": creds["client_email"],
        "scope": "https://www.googleapis.com/auth/webmasters https://www.googleapis.com/auth/indexing",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }).encode()).rstrip(b"=").decode()
    
    # Sign with private key
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    
    private_key = load_pem_private_key(
        creds["private_key"].encode(),
        password=None,
    )
    
    signature = private_key.sign(
        f"{header}.{payload}".encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    
    jwt_token = f"{header}.{payload}.{signature_b64}"
    
    # Exchange JWT for access token
    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": jwt_token,
        },
        timeout=10,
    )
    
    if resp.status_code == 200:
        return resp.json().get("access_token")
    else:
        print(f"❌ Erro ao obter token: {resp.status_code} - {resp.text[:200]}")
        return None

def request_indexing(url, access_token):
    """Request indexing for a single URL."""
    import httpx
    
    # Step 1: Submit URL for indexing
    resp = httpx.post(
        "https://indexing.googleapis.com/v3/urlNotifications:publish",
        json={
            "url": url,
            "type": "URL_UPDATED",
        },
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )
    
    return resp.json()

def get_published_urls():
    """Get all published article URLs from WordPress."""
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    
    from app import _byethost_session, _load_env_dict
    import os
    
    for k, v in _load_env_dict().items():
        os.environ.setdefault(k, v)
    
    client = _byethost_session()
    base = "https://tech-tips.byethost4.com/wp-json/wp/v2/posts"
    resp = client.get(
        f"{base}?per_page=100&status=publish",
        auth=("heltonhb", os.environ.get("WP_APP_PASSWORD", "")),
        timeout=15,
    )
    
    if resp.status_code == 200:
        posts = resp.json()
        urls = []
        seen = set()
        for post in posts:
            link = post.get("link", "")
            if link and link not in seen:
                seen.add(link)
                urls.append({
                    "url": link,
                    "title": post.get("title", {}).get("rendered", ""),
                })
        return urls
    return []

def main():
    """Main function - request indexing for all published URLs."""
    print("🚀 Google Search Console - Solicitando Indexação\n")
    
    # Check credentials
    creds = get_credentials()
    if not creds:
        print("❌ Arquivo google-search-console.json não encontrado!")
        print("\n📋 Como obter:")
        print("1. Acesse: https://console.cloud.google.com")
        print("2. Crie projeto → Ative Search Console API")
        print("3. Crie Service Account → Baixe chave JSON")
        print("4. Salve como google-search-console.json na raiz do projeto")
        print("5. Adicione o email do service account como Proprietário no Search Console")
        return
    
    # Get access token
    print("🔑 Obtendo token de acesso...")
    token = get_access_token()
    if not token:
        return
    print("✅ Token obtido!\n")
    
    # Get URLs
    print("📋 Buscando artigos publicados...")
    urls = get_published_urls()
    print(f"✅ {len(urls)} artigos encontrados\n")
    
    # Request indexing
    print("📝 Solicitando indexação...\n")
    success = 0
    errors = 0
    
    for item in urls:
        url = item["url"]
        title = item["title"][:50]
        
        result = request_indexing(url, token)
        
        if "urlNotificationMetadata" in result:
            print(f"  ✅ {title}")
            success += 1
        elif "error" in result:
            error_msg = result["error"].get("message", "Unknown error")
            if "already" in error_msg.lower() or "pending" in error_msg.lower():
                print(f"  ⏳ {title} (já pendente)")
                success += 1
            else:
                print(f"  ❌ {title}: {error_msg}")
                errors += 1
        else:
            print(f"  ⚠️ {title}: Resposta inesperada")
            errors += 1
    
    print(f"\n{'='*50}")
    print(f"📊 Resultado: {success} sucesso, {errors} erros")
    print(f"⏱️ Indexação pode levar de 1 dia a 2 semanas")

if __name__ == "__main__":
    main()
