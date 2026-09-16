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

def get_pin_image_url(post: dict, client=None) -> str:
    """Extrai URL DIRETA do arquivo de imagem destacada do post.

    O Pinterest rejeita o endpoint REST (`/wp-json/.../media/N`); ele precisa
    da URL do arquivo de imagem. Buscamos o campo `source_url` na API do WP.
    """
    media_id = post.get("featured_media")
    if media_id:
        media_url = f"https://tech-tips.byethost4.com/wp-json/wp/v2/media/{media_id}"
        try:
            if client is not None:
                r = client.get(media_url, timeout=15)
            else:
                import httpx
                with httpx.Client(timeout=15) as c:
                    r = c.get(media_url)
            if r.status_code == 200:
                ctype = r.headers.get("content-type", "")
                if "application/json" in ctype:
                    src = r.json().get("source_url")
                    if src:
                        return src
        except Exception:
            pass

    # Fallback: Pollinations
    title = post.get("title", {}).get("rendered", "tech article")
    import urllib.parse
    prompt = urllib.parse.quote(f"professional tech blog pin, {title}")
    return f"https://image.pollinations.ai/prompt/{prompt}?width=1000&height=1500&nologo=true"

def load_published_pins() -> list:
    """Carrega pins já publicados, unificando as DUAS fontes de dedup.

    Fonte 1: dashboard/data/pinterest_published.json (CLI)
    Fonte 2: dashboard/data/pinterest_config.json["published_pins"] (pipeline/UI)
    A chave de dedup é `article_url` (ou `link`) para evitar duplicação entre fluxos.
    """
    from pathlib import Path
    base = Path(__file__).parent.parent / "dashboard" / "data"
    pub_path = base / "pinterest_published.json"
    cfg_path = base / "pinterest_config.json"

    seen = {}
    for path, key_field in ((pub_path, "article_url"), (cfg_path, "link")):
        if path.exists():
            try:
                data = json.loads(path.read_text())
            except Exception:
                continue
            items = data if isinstance(data, list) else data.get("published_pins", [])
            if not isinstance(items, list):
                continue
            for p in items:
                if not isinstance(p, dict):
                    continue
                k = p.get("article_url") or p.get("link")
                if k:
                    seen[k] = p
    return list(seen.values())

def save_published_pin(pin_data: dict):
    """Salva pin publicado espelhando em AMBAS as fontes de dedup."""
    from pathlib import Path
    base = Path(__file__).parent.parent / "dashboard" / "data"
    base.mkdir(parents=True, exist_ok=True)
    pub_path = base / "pinterest_published.json"
    cfg_path = base / "pinterest_config.json"

    # Fonte 1: pinterest_published.json (lista)
    pins = json.loads(pub_path.read_text()) if pub_path.exists() else []
    if not isinstance(pins, list):
        pins = []
    pins.append(pin_data)
    pub_path.write_text(json.dumps(pins, indent=2, default=str))

    # Fonte 2: pinterest_config.json["published_pins"] (dict)
    cfg = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
        except Exception:
            cfg = {}
    if not isinstance(cfg, dict):
        cfg = {}
    published = cfg.get("published_pins", [])
    if not isinstance(published, list):
        published = []
    published.append({
        "pin_id": pin_data.get("pin_id"),
        "title": pin_data.get("title"),
        "article": pin_data.get("article_url"),
        "created_at": pin_data.get("created_at"),
    })
    cfg["published_pins"] = published[-50:]
    cfg_path.write_text(json.dumps(cfg, indent=2, default=str))


def refresh_access_token() -> str:
    """Tenta renovar o access token via refresh token. Retorna o novo token ou ''.

    Exige PINTEREST_CLIENT_ID / CLIENT_SECRET / REFRESH_TOKEN no .env.
    """
    client_id = os.environ.get("PINTEREST_CLIENT_ID", "")
    client_secret = os.environ.get("PINTEREST_CLIENT_SECRET", "")
    refresh_token = os.environ.get("PINTEREST_REFRESH_TOKEN", "")
    if not (client_id and client_secret and refresh_token):
        return ""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from pinterest_setup import refresh_token as do_refresh, save_token_to_env
        data = do_refresh(client_id, client_secret, refresh_token)
        new_token = data.get("access_token", "")
        if new_token:
            save_token_to_env(new_token, data.get("refresh_token") or "")
            os.environ["PINTEREST_ACCESS_TOKEN"] = new_token
        return new_token
    except Exception as e:
        print(f"   ⚠️ Falha no refresh automático: {e}")
        return ""

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def create_pin(token: str, board_id: str, title: str, description: str,
               link: str, image_url: str) -> dict:
    """Cria um pin no Pinterest. Em 401/403, tenta renovar o token e refaz 1x."""
    import httpx

    payload = {
        "board_id": board_id,
        "title": title[:100],
        "description": description[:500],
        "link": link,
        "image_source_url": image_url,
    }

    def _post(tok: str) -> "httpx.Response":
        return httpx.post(
            "https://api.pinterest.com/v5/pins",
            json=payload,
            headers=auth_headers(tok),
            timeout=30,
        )

    resp = _post(token)
    if resp.status_code in (401, 403):
        print("   ⚠️ Token expirado/rejeitado — tentando refresh automático...")
        new_token = refresh_access_token()
        if new_token:
            token = new_token
            resp = _post(token)
        else:
            return {"success": False,
                    "error": f"HTTP {resp.status_code}: sem refresh configurado (CLIENT_ID/SECRET/REFRESH). "
                             f"Original: {resp.text[:160]}"}

    if resp.status_code in (200, 201):
        pin = resp.json()
        return {"success": True, "pin_id": pin.get("id")}
    else:
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

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
        headers=auth_headers(token),
        timeout=15,
    )
    if resp.status_code in (401, 403):
        print("⚠️ Token expirado — tentando refresh automático...")
        new_token = refresh_access_token()
        if new_token:
            token = new_token
            resp = httpx.get(
                "https://api.pinterest.com/v5/user_account",
                headers=auth_headers(token),
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
    client = httpx.Client(timeout=30)

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
            image_url = get_pin_image_url(post, client=client)
            # Evitar reenvio se já está na lista (ex.: mesclado de outra fonte).
            result = create_pin(token, board_id, title, description, link, image_url)

            # Retry com backoff em rate limit (HTTP 429)
            import time
            if not result["success"] and "429" in result["error"]:
                print("   ⏳ Rate limit (429) — aguardando 30s e tentando de novo...")
                time.sleep(30)
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
