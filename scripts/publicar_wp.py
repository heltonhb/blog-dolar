#!/usr/bin/env python3
"""
Blog em Dolar - Publicador WordPress
Publica artigos gerados via API REST do WordPress
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

try:
    import httpx
except ImportError:
    os.system(f"{sys.executable} -m pip install httpx -q")
    import httpx


class WordPressPublisher:
    def __init__(self, url: str, username: str, app_password: str):
        self.base_url = f"{url.rstrip('/')}/wp-json/wp/v2"
        self.auth = (username, app_password)
    
    def test_connection(self) -> bool:
        """Testa conexao com o WordPress"""
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(f"{self.base_url}/users/me", auth=self.auth)
                if resp.status_code == 200:
                    user = resp.json()
                    print(f"  Conectado como: {user.get('name', 'Unknown')}")
                    return True
                else:
                    print(f"  Erro {resp.status_code}: {resp.text[:200]}")
                    return False
        except Exception as e:
            print(f"  Erro de conexao: {e}")
            return False
    
    def get_categories(self) -> dict:
        """Lista categorias existentes"""
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{self.base_url}/categories", auth=self.auth)
            return {c['name']: c['id'] for c in resp.json()}
    
    def create_category(self, name: str) -> int:
        """Cria nova categoria"""
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{self.base_url}/categories",
                auth=self.auth,
                json={"name": name}
            )
            return resp.json().get('id', 0)
    
    def publish_post(self, article: dict, status: str = "draft") -> dict:
        """
        Publica artigo no WordPress
        status: draft, publish, pending
        """
        # Busca ou cria categorias
        existing_cats = self.get_categories()
        cat_ids = []
        for cat_name in article.get('categories', []):
            if cat_name in existing_cats:
                cat_ids.append(existing_cats[cat_name])
            else:
                new_id = self.create_category(cat_name)
                if new_id:
                    cat_ids.append(new_id)
        
        # Prepara payload
        payload = {
            "title": article.get('title', 'Untitled'),
            "content": article.get('content', ''),
            "slug": article.get('slug', ''),
            "excerpt": article.get('meta_description', ''),
            "status": status,
            "categories": cat_ids,
            "meta": {
                "_yoast_wpseo_metadesc": article.get('meta_description', '')
            }
        }
        
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{self.base_url}/posts",
                auth=self.auth,
                json=payload
            )
            
            if resp.status_code in [200, 201]:
                post = resp.json()
                return {
                    "success": True,
                    "id": post.get('id'),
                    "link": post.get('link'),
                    "status": post.get('status')
                }
            else:
                return {
                    "success": False,
                    "error": resp.text[:500]
                }


def load_config() -> dict:
    """Carrega configuracao"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    
    if not config_path.exists():
        print("ERRO: config/config.yaml nao encontrado!")
        print("Copie config/config.yaml.example e preencha.")
        sys.exit(1)
    
    # Leitura simples de YAML (sem pyyaml)
    config = {}
    with open(config_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and ':' in line:
                key, _, val = line.partition(':')
                config[key.strip()] = val.strip().strip('"')
    
    return config


def publish_from_file(filepath: Path, wp: WordPressPublisher):
    """Publica artigo de arquivo markdown"""
    content = filepath.read_text(encoding="utf-8")
    
    # Extrai frontmatter
    article = {"content": content}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            article['content'] = parts[2].strip()
            
            for line in frontmatter.strip().split("\n"):
                if ':' in line:
                    key, _, val = line.partition(':')
                    article[key.strip()] = val.strip().strip('"[]').split(',')
    
    # Publica
    result = wp.publish_post(article, status="draft")
    
    if result['success']:
        print(f"  Publicado! ID: {result['id']}")
        print(f"  Link: {result['link']}")
    else:
        print(f"  Erro: {result['error']}")
    
    return result


if __name__ == "__main__":
    print("=" * 50)
    print("  BLOG EM DOLAR - Publicador WordPress")
    print("=" * 50)
    
    # Config
    config = load_config()
    
    wp_url = config.get('wordpress_url', '')
    wp_user = config.get('wordpress_username', '')
    wp_pass = config.get('wordpress_app_password', '')
    
    if not all([wp_url, wp_user, wp_pass]):
        print("\nConfigure wordpress_url, wordpress_username, wordpress_app_password")
        print("em config/config.yaml")
        sys.exit(1)
    
    wp = WordPressPublisher(wp_url, wp_user, wp_pass)
    
    # Testa conexao
    print("\nTestando conexao...")
    if not wp.test_connection():
        print("Falha na conexao!")
        sys.exit(1)
    
    # Lista artigos pendentes
    articles_dir = Path(__file__).parent.parent / "articles"
    articles = list(articles_dir.glob("2*.md"))
    
    if not articles:
        print("\nNenhum artigo para publicar.")
        print("Execute primeiro: python scripts/gerar_artigos.py")
        sys.exit(0)
    
    print(f"\n{len(articles)} artigo(s) encontrado(s):")
    for i, a in enumerate(articles, 1):
        print(f"  {i}. {a.name}")
    
    # Publica
    choice = input("\nPublicar qual? (numero, 'all' ou Enter para sair): ").strip()
    
    if choice.lower() == 'all':
        for a in articles:
            print(f"\nPublicando {a.name}...")
            publish_from_file(a, wp)
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(articles):
            print(f"\nPublicando {articles[idx].name}...")
            publish_from_file(articles[idx], wp)
    
    print("\nPronto!")
