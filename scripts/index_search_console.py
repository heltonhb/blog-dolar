#!/usr/bin/env python3
"""Google Search Console Indexer - Solicita indexação de URLs automaticamente."""
import sys
from pathlib import Path

# Adicionar path do dashboard para importar o google_auth compartilhado
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

from google_auth import get_access_token, SEARCH_CONSOLE_SCOPE  # noqa: E402


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
    import os
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / ".env")

    from app import _byethost_session, _load_env_dict

    for k, v in _load_env_dict().items():
        os.environ.setdefault(k, v)

    client = _byethost_session()
    base = "https://tech-tips.ct.ws/wp-json/wp/v2/posts"
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

    # Get access token via auth compartilhada (OAuth de usuário preferido)
    print("🔑 Obtendo token de acesso...")
    token = get_access_token(SEARCH_CONSOLE_SCOPE)
    if not token:
        print("❌ Autenticação Google falhou (sem access token).")
        print("   1. Configure no .env: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET")
        print("   2. Gere o refresh_token: python scripts/analytics_ga4.py --auth")
        print("      (escopo já inclui Search Console — webmasters + indexing)")
        print("   OU fluxo antigo: coloque google-search-console.json na raiz.")
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