#!/usr/bin/env python3
"""
Google Indexing via Sitemap Ping — não precisa de Service Account.
Envia o sitemap para o Google para indexação.
"""
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

SITEMAP_URL = "https://tech-tips.ct.ws/wp-sitemap.xml"

def ping_google():
    """Envia sitemap para o Google via ping."""
    ping_url = f"https://www.google.com/ping?sitemap={SITEMAP_URL}"
    print(f"📡 Enviando sitemap para Google...")
    print(f"   URL: {SITEMAP_URL}\n")
    
    resp = httpx.get(ping_url, timeout=15, follow_redirects=True)
    
    if resp.status_code == 200:
        print("✅ Sitemap enviado com sucesso!")
        print("   O Google irá rastrear o sitemap em breve.")
    else:
        print(f"⚠️ Resposta: {resp.status_code}")
        print(f"   {resp.text[:200]}")

def ping_bing():
    """Envia sitemap para o Bing."""
    ping_url = f"https://www.bing.com/ping?sitemap={SITEMAP_URL}"
    print(f"\n📡 Enviando sitemap para Bing...")
    
    resp = httpx.get(ping_url, timeout=15, follow_redirects=True)
    
    if resp.status_code == 200:
        print("✅ Sitemap enviado para Bing!")
    else:
        print(f"⚠️ Bing: {resp.status_code}")

def submit_url_to_google(url: str):
    """Submete URL individual via Google Search Console (sem API).
    
    Na verdade, isso requer login. Melhor usar o sitemap ping.
    """
    pass

if __name__ == "__main__":
    print("=" * 50)
    print("  Google/Bing Indexing — Sitemap Ping")
    print("=" * 50)
    print()
    ping_google()
    ping_bing()
    print("\n💡 Para indexação mais rápida:")
    print("   1. Acesse: https://search.google.com/search-console")
    print("   2. Selecione tech-tips.ct.ws")
    print("   3. Use 'Inspecionar URL' para cada artigo importante")
    print("   4. Clique 'Solicitar indexação'")
