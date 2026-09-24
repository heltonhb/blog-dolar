#!/usr/bin/env python3
"""
internal_links.py — Internal linking automático entre os posts do blog.

Lê os posts vivos via REST, calcula similaridade por palavras-chave e
insere um bloco "Related Articles" com 2-3 links internos em cada post.

Uso:
    python internal_links.py --dry-run    # mostra o plano de links sem aplicar
    python internal_links.py --apply      # aplica via REST e limpa o cache
"""
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from antibot import SITE  # noqa: E402
from fetch_wp_post import _rest_get, _auth_header  # noqa: E402

import urllib.request  # noqa: E402


def _listar_posts() -> list[dict]:
    """Lista todos os posts vivos (id, slug, title, link)."""
    url = (
        f"{SITE}/wp-json/wp/v2/posts?per_page=50"
        "&_fields=id,slug,title,link"
    )
    raw = _rest_get(url)
    posts = json.loads(raw)
    return [
        {
            "id": p["id"],
            "slug": p["slug"],
            "title": re.sub(r"<[^>]+>", "", p["title"]["rendered"]).strip(),
            "link": p["link"],
        }
        for p in posts
    ]


STOPWORDS = {
    "the", "a", "an", "to", "of", "in", "on", "for", "and", "or", "is",
    "are", "was", "how", "what", "why", "your", "you", "with", "this",
    "that", "it", "its", "from", "by", "at", "as", "be", "best", "guide",
    "ultimate", "2024", "2025", "2026", "beginners", "beginner", "tips",
    "explained", "understanding", "introduction", "vs", "top",
}


def _tokens(texto: str) -> set[str]:
    limpo = re.sub(r"[^a-z0-9\s]", " ", texto.lower())
    return {
        t for t in limpo.split()
        if len(t) >= 4 and t not in STOPWORDS
    }


def _similaridade(a: dict, b: dict, conteudos: dict) -> float:
    """Jaccard entre títulos + corpo completo (idêntico a TF-IDF leve)."""
    ta = _tokens(a["title"] + " " + conteudos.get(a["slug"], ""))
    tb = _tokens(b["title"] + " " + conteudos.get(b["slug"], ""))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# Limiar mínimo: abaixo disso o link é ruído (ex.: git ↔ power bank)
SCORE_MINIMO = 0.06


def montar_plano(max_links: int = 3) -> dict[str, list[dict]]:
    """Para cada post, os N posts mais similares (excluindo ele próprio)."""
    posts = _listar_posts()
    conteudos = {}
    for p in posts:
        try:
            from fetch_wp_post import fetch_post_by_slug

            post = fetch_post_by_slug(p["slug"])
            conteudos[p["slug"]] = post["content_html"] if post else ""
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ corpo indisponível p/ {p['slug']}: {e}", file=sys.stderr)
            conteudos[p["slug"]] = ""

    plano: dict[str, list[dict]] = {}
    for a in posts:
        similares = []
        for b in posts:
            if a["slug"] == b["slug"]:
                continue
            s = _similaridade(a, b, conteudos)
            if s >= SCORE_MINIMO:
                similares.append({**b, "score": round(s, 4)})
        similares.sort(key=lambda x: -x["score"])
        plano[a["slug"]] = similares[:max_links]
    return plano


BLOCO_RELATED = (
    "\n\n<!-- internal-links -->\n"
    "<h3>Related Articles</h3>\n<ul>\n{items}\n</ul>\n"
    "<!-- /internal-links -->\n"
)


def montar_bloco(relacionados: list[dict]) -> str:
    items = "\n".join(
        f'<li><a href="{r["link"]}">{r["title"]}</a></li>'
        for r in relacionados
    )
    return BLOCO_RELATED.format(items=items)


def _posts_com_conteudo() -> dict[int, str]:
    """id → content_html de todos os posts (para editar)."""
    url = f"{SITE}/wp-json/wp/v2/posts?per_page=50&_fields=id,slug,content"
    raw = _rest_get(url)
    return {p["id"]: p["content"]["rendered"] for p in json.loads(raw)}


def _atualizar_post(post_id: int, novo_content: str) -> bool:
    """PUT no post via REST, atravessando o anti-bot (cookie __test).

    O anti-bot responde HTTP 200 com HTML do challenge — enganava o
    status-check antigo. Agora: PUT com cookie e resposta deve ser JSON.
    """
    import urllib.error

    url = f"{SITE}/wp-json/wp/v2/posts/{post_id}"

    def _put(extra: dict | None = None) -> str:
        headers = {
            "Content-Type": "application/json",
            # O anti-bot valida o UA na ESCRITA: 'Mozilla/5.0' passa,
            # UA customizado recebe o challenge mesmo com cookie válido.
            "User-Agent": "Mozilla/5.0",
        }
        headers.update(_auth_header())
        if extra:
            headers.update(extra)
        req = urllib.request.Request(
            url, data=json.dumps({"content": novo_content}).encode(),
            headers=headers, method="PUT",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:150]}") from e

    from antibot import obter_cookie

    cookie = obter_cookie()
    corpo = _put({"Cookie": f"__test={cookie}"} if cookie else None)
    if "toNumbers" in corpo:  # challenge na resposta = PUT não chegou ao WP
        cookie = obter_cookie(force=True)
        corpo = _put({"Cookie": f"__test={cookie}"})
    if not corpo.strip().startswith("{"):
        print(f"    ✗ anti-bot bloqueou o PUT do post {post_id}")
        return False
    return True


def aplicar(plano: dict[str, list[dict]]) -> None:
    """Insere o bloco Related em cada post (substituindo bloco antigo)."""
    posts = _listar_posts()
    por_slug = {p["slug"]: p for p in posts}

    atualizados = 0
    for slug, relacionados in plano.items():
        if not relacionados:
            continue
        p = por_slug[slug]
        post = None
        from fetch_wp_post import fetch_post_by_slug

        post = fetch_post_by_slug(slug)
        if not post:
            continue
        content = post["content_html"]

        # remove bloco antigo, se existir
        content = re.sub(
            r"\s*<!-- internal-links -->.*?<!-- /internal-links -->",
            "",
            content,
            flags=re.DOTALL,
        )
        novo = content.rstrip() + montar_bloco(relacionados)

        if _atualizar_post(p["id"], novo):
            atualizados += 1
            print(f"  ✓ {slug} ← {len(relacionados)} links")
        else:
            print(f"  ✗ falhou: {slug}")

    print(f"\n{atualizados} post(s) atualizado(s) com links internos")


def main():
    args = sys.argv[1:]
    if "--dry-run" in args:
        plano = montar_plano()
        for slug, rels in plano.items():
            print(f"\n── {slug}")
            for r in rels:
                print(f"   {r['score']:.3f}  {r['title'][:60]}")
    elif "--apply" in args:
        plano = montar_plano()
        aplicar(plano)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
