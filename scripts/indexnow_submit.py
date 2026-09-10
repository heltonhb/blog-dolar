#!/usr/bin/env python3
"""
IndexNow — Submete URLs para Bing/Yandex sem autenticação.
Compatível com: Bing, Yandex, Naver, Seznam, Yep.
Google NÃO suporta IndexNow (usa Search Console).
"""
import json, hashlib, httpx
from pathlib import Path
from datetime import datetime

HOST = "tech-tips.byethost4.com"
SITEMAP_URL = f"https://{HOST}/wp-sitemap.xml"

def get_urls_from_sitemap() -> list:
    """Busca URLs do sitemap do WordPress."""
    resp = httpx.get(SITEMAP_URL, timeout=15)
    if resp.status_code != 200:
        print(f"❌ Erro ao acessar sitemap: {resp.status_code}")
        return []
    
    # O sitemap do WP retorna sub-sitemaps
    urls = []
    content = resp.text
    
    # Extrair URLs do sitemap principal
    import re
    sub_sitemaps = re.findall(r'<loc>(.*?)</loc>', content)
    
    for sub_url in sub_sitemaps:
        if 'posts-post' in sub_url:
            resp2 = httpx.get(sub_url, timeout=15)
            if resp2.status_code == 200:
                article_urls = re.findall(r'<loc>(.*?)</loc>', resp2.text)
                urls.extend(article_urls)
                print(f"  📄 {sub_url.split('/')[-1]}: {len(article_urls)} URLs")
    
    return urls

def submit_to_indexnow(urls: list, key: str = None):
    """Submete URLs para IndexNow.
    
    Se não tiver key, gera uma e salva no .well-known/
    """
    if not key:
        # Gera uma key aleatória
        key = hashlib.md5(f"{HOST}-{datetime.now().isoformat()}".encode()).hexdigest()
        print(f"  🔑 Key gerada: {key}")
        print(f"  📝 Para completar, salve esta key em:")
        print(f"     https://{HOST}/.well-known/{key}.txt")
        print(f"     (Arquivo deve conter apenas a key)")
    
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": f"https://{HOST}/.well-known/{key}.txt",
        "urlList": urls[:100],  # Max 10.000 por request
    }
    
    # Submete para Bing (principal IndexNow endpoint)
    resp = httpx.post(
        "https://api.indexnow.org/indexnow",
        json=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=30,
    )
    
    if resp.status_code == 200:
        print(f"✅ IndexNow: {len(urls)} URLs submetidas com sucesso!")
    elif resp.status_code == 202:
        print(f"✅ IndexNow: {len(urls)} URLs aceitas (processamento assíncrono)")
    else:
        print(f"⚠️ IndexNow: {resp.status_code} - {resp.text[:200]}")
    
    return resp.status_code

if __name__ == "__main__":
    print("=" * 50)
    print("  IndexNow — Submissão de URLs")
    print("=" * 50)
    print()
    
    print("📋 Buscando URLs do sitemap...")
    urls = get_urls_from_sitemap()
    
    if not urls:
        print("❌ Nenhuma URL encontrada")
        exit(1)
    
    print(f"\n✅ {len(urls)} URLs encontradas")
    print(f"\n🚀 Submetendo para IndexNow (Bing)...")
    
    # Verificar se já existe uma key
    key_file = Path(__file__).parent.parent / ".well-known" / "indexnow-key.txt"
    key = None
    if key_file.exists():
        key = key_file.read_text().strip()
        print(f"  🔑 Key existente: {key[:16]}...")
    
    submit_to_indexnow(urls, key)
    
    print(f"\n💡 Para Google, use o Search Console:")
    print(f"   https://search.google.com/search-console")
    print(f"   → Inspecionar URL → Solicitar indexação")
