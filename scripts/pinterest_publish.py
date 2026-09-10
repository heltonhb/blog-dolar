#!/usr/bin/env python3
"""
Pinterest Automation — Cria pins automaticamente para artigos publicados.
Uso: python scripts/pinterest_publish.py [--dry-run] [--all] [--last N]
"""
import json, os, sys, re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

def get_wp_posts():
    """Busca artigos publicados no WordPress."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))
    from app import _byethost_session, _load_env_dict

    env = _load_env_dict()
    for k, v in env.items():
        os.environ.setdefault(k, v)

    client = _byethost_session()
    resp = client.get(
        "https://tech-tips.byethost4.com/wp-json/wp/v2/posts",
        params={"per_page": 100, "status": "publish"},
        auth=(env.get("WP_USER", ""), env.get("WP_APP_PASSWORD", "")),
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json()
    return []

def get_pin_image_url(post: dict) -> str:
    """Extrai URL da imagem destacada do post."""
    # Featured media
    media_id = post.get("featured_media")
    if media_id:
        return f"https://tech-tips.byethost4.com/wp-json/wp/v2/media/{media_id}"

    # Fallback: Pollinations
    title = post.get("title", {}).get("rendered", "tech article")
    import urllib.parse
    prompt = urllib.parse.quote(f"professional tech blog pin, {title}")
    return f"https://image.pollinations.ai/prompt/{prompt}?width=1000&height=1500&nologo=true"

def create_pin(token: str, board_id: str, title: str, description: str,
               link: str, image_url: str) -> dict:
    """Cria um pin no Pinterest."""
    import httpx

    payload = {
        "board_id": board_id,
        "title": title[:100],
        "description": description[:500],
        "link": link,
        "image_source_url": image_url,
    }

    resp = httpx.post(
        "https://api.pinterest.com/v5/pins",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if resp.status_code in (200, 201):
        pin = resp.json()
        return {"success": True, "pin_id": pin.get("id")}
    else:
        return {"success": False, "error": resp.text[:200]}

def load_published_pins() -> list:
    """Carrega lista de pins já publicados."""
    path = Path(__file__).parent.parent / "dashboard" / "data" / "pinterest_published.json"
    if path.exists():
        return json.loads(path.read_text())
    return []

def save_published_pin(pin_data: dict):
    """Salva pin publicado na lista."""
    path = Path(__file__).parent.parent / "dashboard" / "data" / "pinterest_published.json"
    pins = load_published_pins()
    pins.append(pin_data)
    path.write_text(json.dumps(pins, indent=2, default=str))

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Pinterest Auto-Publisher")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que faria sem criar pins")
    parser.add_argument("--all", action="store_true", help="Publica pins para todos os artigos")
    parser.add_argument("--last", type=int, default=0, help="Publica pins para os últimos N artigos")
    parser.add_argument("--board-id", type=str, help="Board ID do Pinterest")
    args = parser.parse_args()

    print("=" * 50)
    print("  Pinterest Auto-Publisher")
    print("=" * 50)
    print()

    # Load config
    token = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
    board_id = args.board_id or os.environ.get("PINTEREST_BOARD_ID", "")

    if not token:
        print("❌ PINTEREST_ACCESS_TOKEN não configurado no .env")
        print("   Aguarde a aprovação do trial Pinterest e configure:")
        print("   PINTEREST_ACCESS_TOKEN=pina_...")
        print("   PINTEREST_BOARD_ID=...")
        sys.exit(1)

    if not board_id:
        print("❌ PINTEREST_BOARD_ID não configurado")
        print("   Rodar: python scripts/pinterest_setup.py para descobrir o board")
        sys.exit(1)

    # Test connection
    import httpx
    resp = httpx.get(
        "https://api.pinterest.com/v5/user_account",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"❌ Token inválido ou expirado: {resp.status_code}")
        print("   Regenere o token em: https://developers.pinterest.com/apps/")
        sys.exit(1)

    username = resp.json().get("username", "?")
    print(f"✅ Conectado como: {username}")

    # Get posts
    print("\n📋 Buscando artigos...")
    posts = get_wp_posts()
    published_pins = load_published_pins()
    published_urls = {p.get("article_url") for p in published_pins}

    # Filter
    if args.last > 0:
        posts = posts[:args.last]
    elif not args.all:
        posts = [p for p in posts if p.get("link") not in published_urls]

    if not posts:
        print("✅ Todos os artigos já têm pins!")
        sys.exit(0)

    print(f"📝 {len(posts)} artigos para publicar\n")

    # Create pins
    success = 0
    errors = 0

    for post in posts:
        title = post.get("title", {}).get("rendered", "Untitled")
        link = post.get("link", "")
        excerpt = re.sub(r'<[^>]+>', '', post.get("excerpt", {}).get("rendered", ""))
        description = excerpt[:490] if excerpt else f"Read about {title}"

        print(f"📌 {title[:50]}...")
        print(f"   Link: {link}")

        if args.dry_run:
            print(f"   [DRY RUN] Seria criado pin")
            success += 1
        else:
            image_url = get_pin_image_url(post)
            result = create_pin(token, board_id, title, description, link, image_url)

            if result["success"]:
                print(f"   ✅ Pin criado: {result['pin_id']}")
                save_published_pin({
                    "pin_id": result["pin_id"],
                    "article_url": link,
                    "title": title,
                    "created_at": datetime.now().isoformat(),
                })
                success += 1
            else:
                print(f"   ❌ Erro: {result['error']}")
                errors += 1

        print()

    print("=" * 50)
    print(f"📊 Resultado: {success} sucesso, {errors} erros")
    print("=" * 50)

if __name__ == "__main__":
    main()
