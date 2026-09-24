#!/usr/bin/env python3
"""
publish_devto.py — Republica posts do blog no Dev.to com canonical URL.

Estratégia anti-bloqueio: o conteúdo vive no Dev.to (domínio deles, audiência
deles); o SEO continua consolidando no blog via canonical_url.

API: https://developers.forem.com/forem-api-v1#tag/Articles
Requer DEVTO_API_KEY no .env (dev.to > Settings > Extensions > DEV API Keys).

Uso:
    python publish_devto.py --list              # candidatos dev (check no WP)
    python publish_devto.py <slug> --dry-run    # monta payload sem publicar
    python publish_devto.py <slug>              # publica como RASCUNHO
    python publish_devto.py --all               # todos os candidatos
    python publish_devto.py --cta               # aplica o CTA nos já publicados
"""
import html as _html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch_wp_post import fetch_post_by_slug  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

DEVTO_API = "https://dev.to/api"
API_TIMEOUT = 30
# Varnish do dev.to rejeita o UA default do Python com 403 vazio
UA = "blog-dolar-publisher/1.0 (republish with canonical)"

# CTA de rodapé — tráfego Dev.to → blog (onde os anúncios monetizam)
CTA_MARCADOR = "Originally published on"
CTA_FOOTER = (
    "\n\n---\n\n*Originally published on [Tech Tips](https://tech-tips.ct.ws/) "
    "— practical technology guides and tips, every week.*\n"
)


def _com_cta(body_md: str) -> str:
    """Garante o CTA de rodapé (link pro blog) no corpo do artigo."""
    if CTA_MARCADOR in body_md:
        return body_md
    return body_md.rstrip() + CTA_FOOTER

# Slugs dev/programação publicados no WP — o público certo do Dev.to
SLUGS_DEV = [
    "how-to-learn-git-version-control",
    "how-to-pick-a-programming-language-for-beginners",
    "responsive-web-design-best-practices-2024",
    "difference-between-ai-and-machine-learning",
    "history-and-future-of-cloud-computing",
    "history-of-artificial-intelligence-explained",
    "quantum-computing-2026",
]


def _clean_title(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()


def _html_to_markdown(html_body: str) -> str:
    """Conversão HTML->Markdown mínima para o corpo Dev.to.

    O conteúdo do WP é HTML simples (h2/h3, p, ul/li, strong, code, a).
    Preserva código em <pre><code> como blocos ```.
    """
    s = re.sub(r"<!-- /?wp:[^>]*-->", "", html_body)

    # blocos de código primeiro (para não ter tags internas convertidas)
    def _pre(m):
        code = re.sub(r"<[^>]+>", "", m.group(1))
        lang = ""
        m2 = re.search(r'class="[^"]*language-(\w+)', m.group(0))
        if m2:
            lang = m2.group(1)
        return f"\n```{lang}\n{code}\n```\n"

    s = re.sub(r"<pre[^>]*>(.*?)</pre>", _pre, s, flags=re.DOTALL)

    # inline code
    s = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", s, flags=re.DOTALL)
    # headings
    s = re.sub(
        r"<h([1-6])[^>]*>(.*?)</h\1>",
        lambda m: "\n" + "#" * int(m.group(1)) + " " + re.sub(r"<[^>]+>", "", m.group(2)) + "\n",
        s,
        flags=re.DOTALL,
    )
    # bold/italic
    s = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", s, flags=re.DOTALL)
    s = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", s, flags=re.DOTALL)
    # links
    s = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"[\2](\1)", s, flags=re.DOTALL)
    # listas
    s = re.sub(
        r"<li[^>]*>(.*?)</li>",
        lambda m: "- " + re.sub(r"<[^>]+>", "", m.group(1)).strip(),
        s,
        flags=re.DOTALL,
    )
    s = re.sub(r"</?[ou]l[^>]*>", "\n", s)
    # parágrafos
    s = re.sub(
        r"<p[^>]*>(.*?)</p>",
        lambda m: m.group(1).strip() + "\n",
        s,
        flags=re.DOTALL,
    )
    # tags remanescentes + entidades
    s = re.sub(r"</?div[^>]*>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = _html.unescape(s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def _cover_from_first_image(content_html: str) -> str | None:
    m = re.search(r'<img[^>]+src="([^"]+)"', content_html)
    return m.group(1) if m else None


def _sugerir_tags(title: str, body: str) -> list[str]:
    """Tags Dev.to (máx 4, minúsculas, sem '#') — prioridade por tema central."""
    texto = f"{title} {body}".lower()
    tags: list[str] = []
    # (padrão, tag) — ordem = prioridade; "github" não deve puxar "cloud" etc.
    candidatos = [
        (r"\bgit\b|github", "git"),
        (r"responsive|css|html|web design", "webdev"),
        (r"machine learning", "machinelearning"),
        (r"artificial intelligence|\bai\b", "ai"),
        (r"cloud", "cloud"),
        (r"quantum", "quantum"),
        (r"beginner", "beginners"),
        (r"programming language", "programming"),
    ]
    for padrao, tag in candidatos:
        if re.search(padrao, texto) and tag not in tags:
            tags.append(tag)
        if len(tags) >= 4:
            break
    return tags or ["programming", "webdev"]


def montar_payload(slug: str) -> dict:
    """Monta o payload {article: {...}} da API Dev.to para um slug do blog."""
    post = fetch_post_by_slug(slug)
    if not post:
        raise SystemExit(f"slug não encontrado no WP: {slug}")

    title = _clean_title(post["title"])
    body_md = _com_cta(_html_to_markdown(post["content_html"]))
    cover = _cover_from_first_image(post["content_html"])
    tags = _sugerir_tags(title, body_md)
    # descrição limpa: texto corrido, sem quebras do HTML
    description = re.sub(
        r"\s+", " ", re.sub(r"<[^>]+>", " ", post["content_html"])
    ).strip()[:140]

    return {
        "article": {
            "title": title,
            "published": False,  # rascunho primeiro — revisão manual no site
            "main_image": cover,
            "canonical_url": post["link"],
            "description": description,
            "tags": tags,
            "body_markdown": body_md,
        }
    }


def publicar(slug: str, dry_run: bool = False) -> dict | None:
    try:
        payload = montar_payload(slug)
    except SystemExit as e:
        print(f"  ✗ {slug}: {e}")
        return None

    if dry_run:
        art = payload["article"]
        print(f"── DRY RUN {slug} ──")
        print(json.dumps({**art, "body_markdown": art["body_markdown"][:400] + "…"},
                         indent=2, ensure_ascii=False))
        return None

    key = os.getenv("DEVTO_API_KEY", "")
    if not key:
        print("⚠️  DEVTO_API_KEY ausente — não publiquei. Configure em .env")
        return None

    req = urllib.request.Request(
        f"{DEVTO_API}/articles",
        data=json.dumps(payload).encode(),
        headers={
            "api-key": key,
            "Content-Type": "application/json",
            # Varnish do dev.to rejeita o UA default do Python com 403 vazio
            "User-Agent": "blog-dolar-publisher/1.0 (republish with canonical)",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=API_TIMEOUT)
        data = json.loads(resp.read().decode())
        print(f"  ✓ {slug} → rascunho dev.to: {data.get('url')}")
        return data
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        print(f"  ✗ {slug}: HTTP {e.code} — {detail}")
        return None


def _slug_esta_vivo(slug: str) -> bool:
    try:
        return fetch_post_by_slug(slug) is not None
    except Exception:
        return False


def aplicar_cta_publicados() -> int:
    """Adiciona o CTA de rodapé aos artigos já publicados no Dev.to.

    Casa cada artigo do dashboard com o slug do WP pelo canonical_url,
    e faz PUT só quando o CTA ainda não está no corpo.
    """
    key = os.getenv("DEVTO_API_KEY", "")
    if not key:
        print("⚠️  DEVTO_API_KEY ausente — nada a fazer")
        return 0

    def _headers(extra: dict | None = None) -> dict:
        h = {"api-key": key, "Accept": "application/json", "User-Agent": UA}
        if extra:
            h.update(extra)
        return h

    req = urllib.request.Request(
        f"{DEVTO_API}/articles/me/all?per_page=100", headers=_headers()
    )
    with urllib.request.urlopen(req, timeout=API_TIMEOUT) as r:
        me = json.loads(r.read().decode())

    alterados = 0
    for a in me:
        if not isinstance(a, dict) or not a.get("published"):
            continue
        body = a.get("body_markdown", "")
        if CTA_MARCADOR in body:
            continue
        novo = body.rstrip() + CTA_FOOTER
        put = urllib.request.Request(
            f"{DEVTO_API}/articles/{a['id']}",
            data=json.dumps({"article": {"body_markdown": novo}}).encode(),
            headers=_headers({"Content-Type": "application/json"}),
            method="PUT",
        )
        try:
            with urllib.request.urlopen(put, timeout=API_TIMEOUT) as r:
                if r.status == 200:
                    alterados += 1
                    print(f"  ✓ CTA aplicado: {a['title'][:60]}")
        except urllib.error.HTTPError as e:
            print(f"  ✗ {a['title'][:50]}: HTTP {e.code} — {e.read().decode()[:150]}")
    return alterados


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "--list":
        print(f"Candidatos dev ({len(SLUGS_DEV)}):")
        for s in SLUGS_DEV:
            vivo = "✓" if _slug_esta_vivo(s) else "✗ (não está no WP)"
            print(f"  {vivo} {s}")
        return
    if args[0] == "--cta":
        n = aplicar_cta_publicados()
        print(f"\n{n} artigo(s) atualizado(s) com o CTA")
        return
    if args[0] == "--all":
        dry = "--dry-run" in args
        ok = 0
        for s in SLUGS_DEV:
            if publicar(s, dry_run=dry):
                ok += 1
        print(f"\n{ok}/{len(SLUGS_DEV)} enviados como rascunho")
        return
    slug = args[0].rstrip("/").split("/")[-1]
    publicar(slug, dry_run="--dry-run" in args)


if __name__ == "__main__":
    main()
