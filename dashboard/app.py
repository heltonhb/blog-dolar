#!/usr/bin/env python3
"""
Blog em Dolar - Dashboard Flask com funcionalidades completas
Pipeline: Ideias -> Gerar Artigo -> Verificar -> Imagem -> Publicar -> Pinterest -> AdCash

Melhorias implementadas:
  - Autenticação com senha via .env (DASHBOARD_PASSWORD)
  - Publicação unificada via WordPress REST API
  - Fix imagem real no Pinterest (upload WP → URL pública)
  - APScheduler integrado com controle via UI
  - Google Trends RSS para ideias orientadas a dados
  - AdCash API real
  - Pipeline com checkpoints por slug
  - Auto-revisão de artigos com Gemini
"""

import json
import os
import re
import ftplib
import hashlib
import subprocess
import sys
from io import BytesIO
from datetime import datetime
from pathlib import Path
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, session,
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", hashlib.sha256(b"blog-dolar-secret-2026").hexdigest())

# Add scripts/ to path so we can import shared modules
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from image_generator import (
    generate_article_image,
    generate_image,
    generate_smart_prompt,
    extract_slug_from_filename,
    inject_inline_images,
    upload_featured_image_wp,
    ASPECT_RATIOS,
    DIMENSIONS,
)

# ---------------------------------------------------------------------------
#  APScheduler setup
# ---------------------------------------------------------------------------
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.start()
    _SCHEDULER_AVAILABLE = True
except ImportError:
    _scheduler = None
    _SCHEDULER_AVAILABLE = False


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)

def _data_path(name: str) -> Path:
    return Path(app.root_path) / "data" / name

def _articles_dir() -> Path:
    return Path(app.root_path).parent / "articles"

def _scripts_dir() -> Path:
    return Path(app.root_path).parent / "scripts"

def _load_json(name: str, default=None):
    p = _data_path(name)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default if default is not None else {}

def _save_json(name: str, data):
    p = _data_path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def _load_env_dict() -> dict:
    """Read .env file into dict."""
    env = {}
    env_path = Path(app.root_path).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env

def _save_env_dict(env: dict):
    """Overwrite .env file."""
    env_path = Path(app.root_path).parent / ".env"
    lines = [f"{k}={v}" for k, v in env.items()]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
#  Authentication
# ---------------------------------------------------------------------------

def _get_dashboard_password() -> str:
    """Return the dashboard password from env/file (never hardcoded)."""
    # Try env first (set at startup), then reload from .env file
    pwd = os.environ.get("DASHBOARD_PASSWORD", "")
    if not pwd:
        env = _load_env_dict()
        pwd = env.get("DASHBOARD_PASSWORD", "")
    return pwd

def login_required(f):
    """Decorator: redirect to /login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _get_dashboard_password():
            # No password set → open mode (backwards compatible)
            return f(*args, **kwargs)
        if not session.get("authenticated"):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Não autenticado"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

@app.route("/login", methods=["GET", "POST"])
def login_page():
    error = ""
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == _get_dashboard_password():
            session["authenticated"] = True
            return redirect(url_for("index"))
        error = "Senha incorreta."
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


# ---------------------------------------------------------------------------
#  Article info extractor
# ---------------------------------------------------------------------------

def _extract_article_info(filepath: Path) -> dict:
    content = filepath.read_text(encoding="utf-8")
    title = filepath.stem.replace("-", " ").title()
    meta_desc = ""
    slug = filepath.stem
    tags = []
    body_text = ""

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                line = line.strip()
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip()
                elif line.startswith("slug:"):
                    slug = line.split(":", 1)[1].strip()
                elif line.startswith("meta_description:"):
                    meta_desc = line.split(":", 1)[1].strip()
                elif line.startswith("tags:"):
                    tags_str = line.split(":", 1)[1].strip()
                    tags = [t.strip().strip('"') for t in tags_str.strip("[]").split(",")]
            body_text = parts[2].strip()
        else:
            body_text = content
    else:
        body_text = content

    body_clean = re.sub(r'<[^>]+>', ' ', body_text)
    body_clean = re.sub(r'\s+', ' ', body_clean).strip()
    excerpt = body_clean[:300].rsplit(" ", 1)[0] + "..." if len(body_clean) > 300 else body_clean

    headings = re.findall(r'<h[23][^>]*>(.*?)</h[23]>', body_text, re.IGNORECASE)
    keywords = [re.sub(r'<[^>]+>', '', h).strip() for h in headings[:5]]

    return {
        "title": title,
        "meta_description": meta_desc,
        "slug": slug,
        "tags": tags,
        "excerpt": excerpt,
        "keywords": keywords,
        "body_length": len(body_clean.split()),
        "body_text": body_text,
    }


def _build_pin_prompt(article_info: dict, usage: str = "pinterest") -> str:
    title = article_info["title"]
    keywords = article_info["keywords"]
    tags = article_info["tags"]
    excerpt = article_info.get("excerpt", "")
    api_key = _env("GEMINI_API_KEY")

    if api_key:
        try:
            target_map = {
                "pinterest": "Pinterest pin (vertical 3:4, eye-catching, social media optimized)",
                "featured": "blog featured hero image (wide 16:9, professional)",
                "inline": "blog section illustration (wide 16:9, informative)",
                "square": "social media square image (1:1)",
            }
            target = target_map.get(usage, "blog illustration")
            return generate_smart_prompt(
                api_key=api_key,
                article_title=title,
                article_excerpt=excerpt,
                keywords=keywords + tags,
                target=target,
            )
        except Exception:
            pass

    import re as _re
    clean_kw = []
    for kw in (keywords + tags):
        cleaned = _re.sub(r'^[\d\.\)]+\s*', '', kw).strip()
        cleaned = _re.sub(r'^[A-Z]\.\s*', '', cleaned).strip()
        cleaned = _re.sub(r'^(Phase|Step|Chapter)\s+\d+[:\.]?\s*', '', cleaned, flags=_re.IGNORECASE).strip()
        words = cleaned.split()
        if 1 <= len(words) <= 4 and len(cleaned) < 35 and len(cleaned) > 3:
            clean_kw.append(cleaned.lower())
    seen = set()
    unique_kw = []
    for kw in clean_kw:
        if kw not in seen:
            seen.add(kw)
            unique_kw.append(kw)
    visual_kw = unique_kw[:3]
    if not visual_kw:
        title_words = [w.lower() for w in title.split() if len(w) > 3]
        visual_kw = title_words[:3]

    slug = article_info.get("slug", "")
    theme_hints = {
        "laptop": "laptops on a modern desk, workspace",
        "monitor": "computer monitors, dual screen desk setup",
        "headphone": "premium headphones, audio listening",
        "wifi": "wireless router, wifi signal waves",
        "build-a-pc": "computer parts, motherboard, graphics card",
        "ssd": "solid state drives, storage hardware",
        "vpn": "digital shield, online security concept",
        "keyboard": "mechanical keyboard, colorful keys",
        "mouse": "computer mouse, ergonomic device",
        "travel": "travel suitcase, world map, adventure",
        "pack": "packed luggage, travel items",
        "privacy": "privacy shield, digital security",
        "speed": "speedometer, fast performance",
        "fix": "repair tools, technical support",
        "guide": "step by step infographic arrows",
        "best": "product comparison lineup, top picks",
        "budget": "affordable price tag, value deal",
        "gaming": "gaming setup, RGB lights",
        "work-from-home": "home office desk, productive workspace",
        "nvme": "NVMe SSD drive, M.2 slot, fast storage",
    }
    theme = next((desc for key, desc in theme_hints.items() if key in slug), "")
    kw_str = ", ".join(visual_kw)
    theme_str = f" Include: {theme}." if theme else ""
    return (
        f"Vibrant Pinterest pin illustration about {kw_str}.{theme_str} "
        f"Colorful flat design, bright gradient background, modern editorial style, "
        f"clean composition, no text, no words, no watermarks. "
        f"High quality, detailed, sharp, 1024x1024."
    )


# ---------------------------------------------------------------------------
#  Gemini API helper
# ---------------------------------------------------------------------------

def _gemini_call(prompt: str, api_key: str = "", model: str = "gemini-flash-lite-latest",
                 temperature: float = 0.7, max_tokens: int = 8192) -> str:
    import httpx
    api_key = api_key or _env("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não configurada")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    last_err = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=90) as client:
                resp = client.post(url, json=payload)
                if resp.status_code in (503, 429):
                    import time; time.sleep(5 * (attempt + 1))
                    last_err = f"HTTP {resp.status_code}"
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            last_err = str(e)
            import time; time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Falha na API Gemini após 3 tentativas: {last_err}")

def _parse_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\[[\s\S]*\]|\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
        raise


# ---------------------------------------------------------------------------
#  WordPress REST API publisher (unified)
# ---------------------------------------------------------------------------

def _wp_publish(article: dict, status: str = "publish") -> dict:
    """Publish via WordPress REST API. Returns {success, id, link, error}."""
    import httpx as _httpx

    env = _load_env_dict()
    site_url = env.get("SITE_URL") or _env("SITE_URL", "https://tech-tips.byethost4.com")
    wp_user = env.get("WP_USER") or _env("WP_USER", "")
    wp_pass = env.get("WP_APP_PASSWORD") or _env("WP_APP_PASSWORD", "")

    if not wp_user or not wp_pass:
        return {"success": False, "error": "Configure WP_USER e WP_APP_PASSWORD nas configurações"}

    base_url = f"{site_url.rstrip('/')}/wp-json/wp/v2"
    auth = (wp_user, wp_pass)

    payload = {
        "title": article.get("title", "Untitled"),
        "content": article.get("content", ""),
        "slug": article.get("slug", ""),
        "excerpt": article.get("meta_description", ""),
        "status": status,
        "meta": {"_yoast_wpseo_metadesc": article.get("meta_description", "")},
    }
    if article.get("featured_media_id"):
        payload["featured_media"] = article["featured_media_id"]

    try:
        client = _byethost_session()
        resp = client.post(f"{base_url}/posts", auth=auth, json=payload)
        if resp.status_code in (200, 201):
            post = resp.json()
            return {"success": True, "id": post.get("id"), "link": post.get("link", ""), "status": post.get("status")}
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _wp_upload_media(image_bytes: bytes, filename: str, alt_text: str = "") -> dict:
    """Upload image to WP media library. Returns {success, id, url, error}."""
    import httpx as _httpx

    env = _load_env_dict()
    site_url = env.get("SITE_URL") or _env("SITE_URL", "https://tech-tips.byethost4.com")
    wp_user = env.get("WP_USER") or _env("WP_USER", "")
    wp_pass = env.get("WP_APP_PASSWORD") or _env("WP_APP_PASSWORD", "")

    if not wp_user or not wp_pass:
        return {"success": False, "error": "WP_USER/WP_APP_PASSWORD não configurados"}

    base_url = f"{site_url.rstrip('/')}/wp-json/wp/v2"
    try:
        client = _byethost_session()
        resp = client.post(
                f"{base_url}/media",
            auth=(wp_user, wp_pass),
            content=image_bytes,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "image/png",
            },
        )
        if resp.status_code in (200, 201):
            media = resp.json()
            media_id = media.get("id")
            media_url = media.get("source_url", "")
            if alt_text and media_id:
                client.post(f"{base_url}/media/{media_id}", auth=(wp_user, wp_pass),
                            json={"alt_text": alt_text})
            return {"success": True, "id": media_id, "url": media_url}
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
#  FTP/Anti-bot helpers (fallback only)
# ---------------------------------------------------------------------------

def _solve_challenge(html: str):
    matches = re.findall(r'toNumbers\("([0-9a-f]+)"\)', html)
    if len(matches) < 3:
        return None
    a, b, c = matches[0], matches[1], matches[2]
    try:
        from Crypto.Cipher import AES
        key = bytes.fromhex(a)
        iv = bytes.fromhex(b)
        ct = bytes.fromhex(c)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(ct)
        pad_len = decrypted[-1]
        if 1 <= pad_len <= 16:
            decrypted = decrypted[:-pad_len]
        return decrypted.hex()
    except Exception:
        return None

def _byethost_session():
    """Create an httpx Client with the ByetHost anti-bot cookie resolved."""
    import httpx as _httpx
    client = _httpx.Client(timeout=30, verify=False, follow_redirects=True)
    try:
        resp = client.get("https://tech-tips.byethost4.com/")
        html = resp.text
        if "toNumbers" in html and "slowAES" in html:
            cookie_val = _solve_challenge(html)
            if cookie_val:
                client.cookies.set("__test", cookie_val, domain=".byethost4.com")
                test = client.get("https://tech-tips.byethost4.com/wp-json/")
                if test.status_code == 200 and "name" in test.text[:200]:
                    return client
                client.get("https://tech-tips.byethost4.com/?i=1")
    except Exception:
        pass
    return client


def _cleanup_ftp(host, user, password):
    try:
        ftp = ftplib.FTP(host, timeout=15)
        ftp.login(user, password)
        ftp.cwd("htdocs")
        for f in ("auto-publish.php", "article_body.html"):
            try:
                ftp.delete(f)
            except Exception:
                pass
        ftp.quit()
    except Exception:
        pass


# ---------------------------------------------------------------------------
#  Pipeline checkpoint helpers (task #11)
# ---------------------------------------------------------------------------

def _checkpoint_path() -> Path:
    return _data_path("pipeline_checkpoints.json")

def _load_checkpoints() -> dict:
    p = _checkpoint_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def _save_checkpoint(slug: str, step: str, value):
    """Mark a pipeline step as done for a given slug."""
    checkpoints = _load_checkpoints()
    if slug not in checkpoints:
        checkpoints[slug] = {}
    checkpoints[slug][step] = value
    checkpoints[slug]["updated_at"] = datetime.now().isoformat()
    _checkpoint_path().parent.mkdir(parents=True, exist_ok=True)
    _checkpoint_path().write_text(json.dumps(checkpoints, indent=2, ensure_ascii=False), encoding="utf-8")

def _get_checkpoint(slug: str, step: str):
    return _load_checkpoints().get(slug, {}).get(step)

def _clear_checkpoint(slug: str):
    checkpoints = _load_checkpoints()
    checkpoints.pop(slug, None)
    _checkpoint_path().write_text(json.dumps(checkpoints, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
#  Scheduled pipeline job
# ---------------------------------------------------------------------------

def _scheduled_pipeline_job(keyword: str):
    """Run the full pipeline for a keyword (called by APScheduler)."""
    with app.app_context():
        try:
            _run_pipeline_logic(
                keyword=keyword,
                pin_prompt="",
                skip_publish=False,
                skip_pinterest=False,
                article_filename="",
                force_restart=False,
            )
        except Exception as e:
            # Log errors to pipeline history as failed runs
            history = _load_json("pipeline_history.json", [])
            history.append({
                "keyword": keyword,
                "title": keyword,
                "steps": [{"step": "scheduler", "status": "error", "error": str(e)}],
                "completed_at": datetime.now().isoformat(),
                "source": "scheduler",
            })
            history = history[-100:]
            _save_json("pipeline_history.json", history)


# ---------------------------------------------------------------------------
#  Core pipeline logic (shared by API and scheduler)
# ---------------------------------------------------------------------------

def _run_pipeline_logic(keyword: str, pin_prompt: str, skip_publish: bool,
                         skip_pinterest: bool, article_filename: str,
                         force_restart: bool = False) -> dict:
    """Execute the full pipeline. Returns the same dict as /api/pipeline."""
    import httpx as _httpx
    import urllib.parse

    steps = []

    # Determine slug for checkpointing
    pipeline_slug = re.sub(r'[^a-z0-9-]', '-', keyword.lower().strip())[:60]

    # ---- Step 1: Article ----
    if article_filename:
        filepath = _articles_dir() / article_filename
        if not filepath.exists():
            return {"success": False, "error": f"Artigo não encontrado: {article_filename}"}
        content = filepath.read_text(encoding="utf-8")
        title, slug, meta_desc = keyword, article_filename.replace(".md", ""), ""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if line.strip().startswith("title:"):
                        title = line.split(":", 1)[1].strip()
                    elif line.strip().startswith("slug:"):
                        slug = line.split(":", 1)[1].strip()
                    elif line.strip().startswith("meta_description:"):
                        meta_desc = line.split(":", 1)[1].strip()
        steps.append({"step": "article", "status": "ok", "filename": article_filename, "title": title})
    else:
        # Check checkpoint
        ckpt_article = _get_checkpoint(pipeline_slug, "article") if not force_restart else None
        if ckpt_article and (_articles_dir() / ckpt_article).exists():
            article_filename = ckpt_article
            filepath = _articles_dir() / article_filename
            info = _extract_article_info(filepath)
            title, slug, meta_desc = info["title"], info["slug"], info["meta_description"]
            steps.append({"step": "article", "status": "ok", "filename": article_filename,
                          "title": title, "from_checkpoint": True})
        else:
            steps.append({"step": "article", "status": "running"})
            prompt = f"""Write a comprehensive blog post about: {keyword}
Target keyword: {keyword}

Requirements:
- 1500-2000 words
- Use keyword naturally 5-8 times
- Include H2 and H3 subheadings
- Add comparison table where relevant
- Use bullet points for readability
- Conversational, engaging tone
- Include a meta description (150 chars)

Return ONLY JSON:
{{
  "title": "SEO title",
  "slug": "url-friendly-slug",
  "meta_description": "...",
  "content": "Full HTML article with <h2>, <h3>, <p>, <ul>, <table> tags",
  "tags": ["tag1", "tag2", "tag3"]
}}"""
            result = _gemini_call(prompt)
            article = _parse_json(result)
            articles_dir = _articles_dir()
            articles_dir.mkdir(exist_ok=True)
            date_str = datetime.now().strftime("%Y-%m-%d")
            slug = article.get("slug", "untitled")
            article_filename = f"{date_str}_{slug}.md"
            filepath = articles_dir / article_filename
            file_content = (
                f"---\ntitle: {article.get('title', 'Untitled')}\ndate: {date_str}\n"
                f"slug: {slug}\nmeta_description: {article.get('meta_description', '')}\n"
                f"tags: {json.dumps(article.get('tags', []))}\n---\n\n{article.get('content', '')}\n"
            )
            filepath.write_text(file_content, encoding="utf-8")
            title = article.get("title", keyword)
            meta_desc = article.get("meta_description", "")
            _save_checkpoint(pipeline_slug, "article", article_filename)
            steps[-1] = {"step": "article", "status": "ok", "filename": article_filename, "title": title}

    # ---- Step 2: Image ----
    image_slug = extract_slug_from_filename(article_filename)
    pin_filename = f"pin-{image_slug}.png"
    images_dir = Path(app.root_path) / "static" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Check checkpoint for image
    ckpt_image = _get_checkpoint(pipeline_slug, "image") if not force_restart else None
    if ckpt_image and (images_dir / ckpt_image).exists():
        pin_filename = ckpt_image
        image_bytes = (images_dir / pin_filename).read_bytes()
        provider = "checkpoint"
        steps.append({"step": "image", "status": "ok", "filename": pin_filename,
                      "size_kb": round(len(image_bytes) / 1024, 1), "provider": provider,
                      "from_checkpoint": True})
    else:
        article_info = _extract_article_info(filepath)
        if not pin_prompt:
            pin_prompt = _build_pin_prompt(article_info, usage="pinterest")
        api_key_img = _env("GEMINI_API_KEY")
        image_bytes, provider = generate_image(prompt=pin_prompt, api_key=api_key_img, usage="pinterest")
        (images_dir / pin_filename).write_bytes(image_bytes)
        # Also generate featured image (best-effort)
        try:
            feat_prompt = _build_pin_prompt(article_info, usage="featured")
            featured_bytes, _ = generate_image(prompt=feat_prompt, api_key=api_key_img, usage="featured")
            (images_dir / f"featured-{image_slug}.png").write_bytes(featured_bytes)
        except Exception:
            pass
        _save_checkpoint(pipeline_slug, "image", pin_filename)
        steps.append({"step": "image", "status": "ok", "filename": pin_filename,
                      "size_kb": round(len(image_bytes) / 1024, 1), "provider": provider})

    # ---- Step 3: Publish to WordPress via REST API ----
    post_url = ""
    public_image_url = ""

    if not skip_publish:
        # Check checkpoint
        ckpt_publish = _get_checkpoint(pipeline_slug, "publish") if not force_restart else None
        if ckpt_publish:
            post_url = ckpt_publish.get("url", "")
            public_image_url = ckpt_publish.get("image_url", "")
            steps.append({"step": "publish", "status": "ok",
                          "post_id": ckpt_publish.get("post_id"), "url": post_url,
                          "from_checkpoint": True})
        else:
            steps.append({"step": "publish", "status": "running"})
            try:
                file_content = filepath.read_text(encoding="utf-8")
                body = file_content
                if file_content.startswith("---"):
                    parts = file_content.split("---", 2)
                    if len(parts) >= 3:
                        body = parts[2].strip()

                article_data = {
                    "title": title,
                    "content": body,
                    "slug": slug,
                    "meta_description": meta_desc,
                }

                # Try to upload featured image and get public URL
                feat_path = images_dir / f"featured-{image_slug}.png"
                if feat_path.exists():
                    media_result = _wp_upload_media(
                        feat_path.read_bytes(),
                        f"featured-{image_slug}.png",
                        alt_text=title,
                    )
                    if media_result["success"]:
                        article_data["featured_media_id"] = media_result["id"]
                        public_image_url = media_result["url"]

                # Upload pin image too (for Pinterest)
                if not public_image_url:
                    pin_path = images_dir / pin_filename
                    if pin_path.exists():
                        pin_media = _wp_upload_media(
                            pin_path.read_bytes(),
                            pin_filename,
                            alt_text=title,
                        )
                        if pin_media["success"]:
                            public_image_url = pin_media["url"]

                pub_result = _wp_publish(article_data, status="publish")
                if pub_result["success"]:
                    post_url = pub_result.get("link", "")
                    _save_checkpoint(pipeline_slug, "publish", {
                        "post_id": pub_result.get("id"),
                        "url": post_url,
                        "image_url": public_image_url,
                    })
                    steps[-1] = {"step": "publish", "status": "ok",
                                 "post_id": pub_result.get("id"), "url": post_url}
                else:
                    steps[-1] = {"step": "publish", "status": "error", "error": pub_result["error"]}
            except Exception as e:
                steps[-1] = {"step": "publish", "status": "error", "error": str(e)}
    else:
        steps.append({"step": "publish", "status": "skipped"})

    # Fallback public image URL: Pollinations (only if WP upload failed)
    if not public_image_url:
        public_image_url = (
            f"https://image.pollinations.ai/prompt/"
            f"{urllib.parse.quote(pin_prompt or title)}?width=768&height=1024&nologo=true"
        )

    # ---- Step 4: Pinterest ----
    if not skip_pinterest:
        # Check checkpoint
        ckpt_pin = _get_checkpoint(pipeline_slug, "pinterest") if not force_restart else None
        if ckpt_pin:
            steps.append({"step": "pinterest", "status": "ok",
                          "pin_id": ckpt_pin, "from_checkpoint": True})
        else:
            steps.append({"step": "pinterest", "status": "running"})
            try:
                access_token = _env("PINTEREST_ACCESS_TOKEN") or _load_json("pinterest_config.json", {}).get("access_token", "")
                board_id = _env("PINTEREST_BOARD_ID") or _load_json("pinterest_config.json", {}).get("board_id", "")
                if not access_token or not board_id:
                    steps[-1] = {"step": "pinterest", "status": "error",
                                 "error": "Pinterest não configurado (ACCESS_TOKEN ou BOARD_ID ausente)"}
                else:
                    pin_payload = {
                        "board_id": board_id,
                        "title": title[:100],
                        "description": (meta_desc or f"Read about {title}")[:500],
                        "link": post_url or _env("SITE_URL", "https://tech-tips.byethost4.com"),
                        "image_source_url": public_image_url,
                    }
                    resp_pin = _httpx.post(
                        "https://api.pinterest.com/v5/pins",
                        json=pin_payload,
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=30,
                    )
                    if resp_pin.status_code in (200, 201):
                        pin_data = resp_pin.json()
                        pin_id = pin_data.get("id", "")
                        config = _load_json("pinterest_config.json", {})
                        published = config.get("published_pins", [])
                        published.append({"pin_id": pin_id, "title": title,
                                          "article": article_filename,
                                          "created_at": datetime.now().isoformat()})
                        config["published_pins"] = published[-50:]
                        _save_json("pinterest_config.json", config)
                        _save_checkpoint(pipeline_slug, "pinterest", pin_id)
                        steps[-1] = {"step": "pinterest", "status": "ok", "pin_id": pin_id}
                    else:
                        steps[-1] = {"step": "pinterest", "status": "error",
                                     "error": f"HTTP {resp_pin.status_code}: {resp_pin.text[:200]}"}
            except Exception as e:
                steps[-1] = {"step": "pinterest", "status": "error", "error": str(e)}
    else:
        steps.append({"step": "pinterest", "status": "skipped"})

    # Save history
    history = _load_json("pipeline_history.json", [])
    if not isinstance(history, list):
        history = []
    history.append({
        "keyword": keyword,
        "article": article_filename,
        "title": title,
        "image": pin_filename,
        "image_url": public_image_url,
        "post_url": post_url,
        "steps": steps,
        "completed_at": datetime.now().isoformat(),
    })
    history = history[-100:]
    _save_json("pipeline_history.json", history)

    # Clean up checkpoint if all steps succeeded
    all_ok = all(s["status"] in ("ok", "skipped") for s in steps)
    if all_ok:
        _clear_checkpoint(pipeline_slug)

    return {
        "success": all_ok,
        "article": article_filename,
        "title": title,
        "image": pin_filename,
        "image_url": public_image_url,
        "post_url": post_url,
        "steps": steps,
    }


# ---------------------------------------------------------------------------
#  Page routes (render templates) — all protected by login_required
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/ideas")
@login_required
def ideas_page():
    return render_template("ideas.html")

@app.route("/generate")
@login_required
def generate_page():
    return render_template("generate.html")

@app.route("/articles")
@login_required
def articles_page():
    return render_template("articles.html")

@app.route("/images")
@login_required
def images_page():
    return render_template("images.html")

@app.route("/publish")
@login_required
def publish_page():
    return render_template("publish.html")

@app.route("/pinterest")
@login_required
def pinterest_page():
    return render_template("pinterest.html")

@app.route("/verify")
@login_required
def verify_page():
    return render_template("verify.html")

@app.route("/adcash")
@login_required
def adcash_page():
    return render_template("adcash.html")

@app.route("/pipeline")
@login_required
def pipeline_page():
    return render_template("pipeline.html")

@app.route("/settings")
@login_required
def settings_page():
    return render_template("settings.html")

@app.route("/scheduler")
@login_required
def scheduler_page():
    return render_template("scheduler.html")


# ---------------------------------------------------------------------------
#  API: Dashboard stats
# ---------------------------------------------------------------------------

@app.route("/api/stats")
@login_required
def api_stats():
    articles_dir = _articles_dir()
    article_count = len(list(articles_dir.glob("2*.md"))) if articles_dir.exists() else 0
    ideas = _load_json("ideas.json", [])
    pending_ideas = sum(1 for i in ideas if i.get("status") == "pending")

    published_count = 0
    try:
        import pymysql
        conn = pymysql.connect(
            host=_env("WP_DB_HOST", "sql310.byetcluster.com"),
            user=_env("WP_DB_USER"), password=_env("WP_DB_PASS"),
            database=_env("WP_DB_NAME"), charset="utf8mb4", connect_timeout=5,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM wpq9_posts WHERE post_status='publish' AND post_type='post'")
            published_count = cur.fetchone()[0]
        conn.close()
    except Exception:
        pass

    adcash = _load_json("adcash_stats.json", {})
    revenue = adcash.get("total_revenue", 0.0)

    # Scheduler status
    scheduler_info = {"running": False, "jobs": []}
    if _SCHEDULER_AVAILABLE and _scheduler:
        scheduler_info["running"] = _scheduler.running
        scheduler_info["jobs"] = [
            {"id": j.id, "next_run": str(j.next_run_time)} for j in _scheduler.get_jobs()
        ]

    return jsonify({
        "article_count": article_count,
        "published_count": published_count,
        "pending_ideas": pending_ideas,
        "revenue": revenue,
        "scheduler": scheduler_info,
    })


# ---------------------------------------------------------------------------
#  API: Ideas (Gemini + Google Trends RSS)
# ---------------------------------------------------------------------------

@app.route("/api/ideas/generate", methods=["POST"])
@login_required
def api_generate_ideas():
    try:
        data = request.json or {}
        source = data.get("source", "ai")  # "ai" or "trends"

        if source == "trends":
            ideas = _generate_ideas_from_trends()
        else:
            ideas = _generate_ideas_from_gemini()

        existing = _load_json("ideas.json", [])
        max_id = max((i.get("id", 0) for i in existing), default=0)
        for idx, idea in enumerate(ideas):
            idea["id"] = max_id + idx + 1
            idea["status"] = "pending"
            idea["created_at"] = datetime.now().isoformat()
            idea["source"] = source

        existing.extend(ideas)
        # Limit: keep last 200 ideas to avoid unbounded growth
        existing = existing[-200:]
        _save_json("ideas.json", existing)
        return jsonify({"success": True, "ideas": ideas, "count": len(ideas)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _generate_ideas_from_gemini() -> list:
    """Generate 10 evergreen tech ideas via Gemini."""
    data = _gemini_call(
        "Generate 10 evergreen technology blog post ideas. "
        "Focus on topics that stay relevant for years. Include long-tail keywords.\n"
        "Return ONLY a JSON array:\n"
        '[{"title":"Article title","keyword":"long-tail keyword","cpm_estimate":"$10-20","category":"technology"}]\n'
        "No markdown, pure JSON."
    )
    return _parse_json(data)


def _generate_ideas_from_trends() -> list:
    """Fetch Google Trends RSS and turn trending topics into article ideas via Gemini."""
    import feedparser

    # Google Trends RSS — public, no API key needed
    feed_url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
    feed = feedparser.parse(feed_url)

    trending = []
    for entry in feed.entries[:20]:
        title = entry.get("title", "")
        if title:
            trending.append(title)

    if not trending:
        # Fallback to pure AI if RSS fails
        return _generate_ideas_from_gemini()

    trends_str = "\n".join(f"- {t}" for t in trending[:15])
    prompt = (
        f"These are currently trending topics on Google in the USA:\n{trends_str}\n\n"
        "Select the 8 topics most relevant to technology, gadgets, software, or computers. "
        "For each, write a specific, SEO-optimized blog article title and long-tail keyword.\n"
        "Return ONLY a JSON array:\n"
        '[{"title":"Article title","keyword":"long-tail keyword","cpm_estimate":"$8-15","category":"technology","trend_source":"google_trends"}]\n'
        "No markdown, pure JSON."
    )
    data = _gemini_call(prompt)
    ideas = _parse_json(data)
    for idea in ideas:
        idea["source"] = "trends"
    return ideas


@app.route("/api/ideas/add", methods=["POST"])
@login_required
def api_add_idea():
    try:
        data = request.json
        existing = _load_json("ideas.json", [])
        max_id = max((i.get("id", 0) for i in existing), default=0)
        new_idea = {
            "id": max_id + 1,
            "title": data.get("title", ""),
            "keyword": data.get("keyword", ""),
            "category": data.get("category", "technology"),
            "cpm_estimate": data.get("cpm_estimate", ""),
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "source": "manual",
        }
        existing.append(new_idea)
        existing = existing[-200:]
        _save_json("ideas.json", existing)
        return jsonify({"success": True, "idea": new_idea})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ideas/delete/<int:idea_id>", methods=["POST"])
@login_required
def api_delete_idea(idea_id):
    try:
        existing = _load_json("ideas.json", [])
        existing = [i for i in existing if i.get("id") != idea_id]
        _save_json("ideas.json", existing)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ideas/list")
@login_required
def api_list_ideas():
    ideas = _load_json("ideas.json", [])
    ideas.sort(key=lambda x: x.get("id", 0), reverse=True)
    return jsonify(ideas)


# ---------------------------------------------------------------------------
#  API: Generate article (Gemini)
# ---------------------------------------------------------------------------

@app.route("/api/generate", methods=["POST"])
@login_required
def api_generate_article():
    try:
        data = request.json or {}
        keyword = data.get("keyword", "").strip()
        if not keyword:
            return jsonify({"success": False, "error": "Palavra-chave obrigatória"}), 400

        prompt = f"""Write a comprehensive blog post about: {keyword}
Target keyword: {keyword}

Requirements:
- 1500-2000 words
- Use keyword naturally 5-8 times
- Include H2 and H3 subheadings
- Add comparison table where relevant
- Use bullet points for readability
- Conversational, engaging tone
- Include a meta description (150 chars)

Return ONLY JSON:
{{
  "title": "SEO title",
  "slug": "url-friendly-slug",
  "meta_description": "...",
  "content": "Full HTML article with <h2>, <h3>, <p>, <ul>, <table> tags",
  "tags": ["tag1", "tag2", "tag3"]
}}"""

        result = _gemini_call(prompt)
        article = _parse_json(result)

        articles_dir = _articles_dir()
        articles_dir.mkdir(exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        slug = article.get("slug", "untitled")
        filename = f"{date_str}_{slug}.md"
        filepath = articles_dir / filename
        content = (
            f"---\ntitle: {article.get('title', 'Untitled')}\ndate: {date_str}\n"
            f"slug: {slug}\nmeta_description: {article.get('meta_description', '')}\n"
            f"tags: {json.dumps(article.get('tags', []))}\n---\n\n{article.get('content', 'No content')}\n"
        )
        filepath.write_text(content, encoding="utf-8")

        return jsonify({
            "success": True,
            "filename": filename,
            "title": article.get("title"),
            "slug": slug,
            "word_count": len(article.get("content", "").split()),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
#  API: Articles list
# ---------------------------------------------------------------------------

@app.route("/api/articles/list")
@login_required
def api_list_articles():
    articles_dir = _articles_dir()
    articles = []
    if articles_dir.exists():
        for f in sorted(articles_dir.glob("2*.md"), reverse=True):
            size_kb = f.stat().st_size / 1024
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            articles.append({
                "filename": f.name,
                "size": f"{size_kb:.1f}",
                "date": mtime.strftime("%d/%m/%Y %H:%M"),
                "mtime": f.stat().st_mtime,
            })
    articles.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    return jsonify(articles)

@app.route("/api/articles/delete/<filename>", methods=["DELETE"])
@login_required
def api_delete_article(filename):
    try:
        filepath = _articles_dir() / filename
        if not filepath.exists():
            return jsonify({"success": False, "error": f"Arquivo não encontrado: {filename}"}), 404
        if not filename.endswith(".md"):
            return jsonify({"success": False, "error": "Apenas arquivos .md podem ser removidos"}), 400
        filepath.unlink()
        return jsonify({"success": True, "filename": filename})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
#  API: Verify article (SEO + Gemini auto-review)
# ---------------------------------------------------------------------------

@app.route("/api/verify", methods=["POST"])
@login_required
def api_verify_article():
    try:
        data = request.json or {}
        filename = data.get("filename", "").strip()
        use_ai = data.get("use_ai", False)
        if not filename:
            return jsonify({"success": False, "error": "Arquivo obrigatório"}), 400

        filepath = _articles_dir() / filename
        if not filepath.exists():
            return jsonify({"success": False, "error": f"Arquivo não encontrado: {filename}"}), 404

        content = filepath.read_text(encoding="utf-8")
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                body = parts[2]

        text = re.sub(r'<[^>]+>', '', body)
        words = text.split()
        word_count = len(words)

        score = 100
        issues = []
        warnings = []

        if word_count < 300:
            score -= 30
            issues.append(f"Artigo muito curto: {word_count} palavras (mínimo 300)")
        elif word_count < 800:
            score -= 10
            warnings.append(f"Artigo curto: {word_count} palavras (recomendado 1500+)")

        h2_count = body.lower().count("<h2")
        h3_count = body.lower().count("<h3")
        if h2_count == 0:
            score -= 20
            issues.append("Sem subtítulos H2")
        elif h2_count < 2:
            score -= 5
            warnings.append(f"Poucos H2: {h2_count} (recomendado 3+)")
        if h3_count == 0 and h2_count > 2:
            warnings.append("Sem subtítulos H3 (recomendado)")

        internal_links = len(re.findall(r'href=["\'](?:/|https?://[^"]*tech-tips)', body))
        external_links = len(re.findall(r'href=["\']https?://(?!tech-tips)', body))
        if internal_links == 0:
            warnings.append("Sem links internos")

        images = body.lower().count("<img")
        if images == 0:
            warnings.append("Sem imagens no artigo")

        if "meta_description" not in content[:500]:
            warnings.append("Sem meta description")

        score = max(0, score)
        status = "Aprovado" if score >= 70 else "Reprovado"

        # --- Gemini AI review (optional, task #12) ---
        ai_review = None
        if use_ai and _env("GEMINI_API_KEY"):
            try:
                article_info = _extract_article_info(filepath)
                ai_prompt = f"""You are an expert SEO editor. Review this blog article and return a JSON evaluation.

Title: {article_info['title']}
Word count: {word_count}
H2 headings: {h2_count}, H3 headings: {h3_count}
Internal links: {internal_links}, External links: {external_links}
Images: {images}

Article excerpt (first 800 chars of body):
{article_info.get('body_text', '')[:800]}

Return ONLY JSON (no markdown):
{{
  "ai_score": <0-100 integer>,
  "readability": "<Excellent|Good|Fair|Poor>",
  "keyword_density": "<Good|Too Low|Too High>",
  "content_quality": "<summary in 1 sentence>",
  "missing_elements": ["list", "of", "missing", "things"],
  "improvements": ["actionable", "suggestion 1", "suggestion 2", "suggestion 3"],
  "seo_verdict": "<Optimized|Needs Work|Poor>"
}}"""
                ai_raw = _gemini_call(ai_prompt, temperature=0.3)
                ai_review = _parse_json(ai_raw)
                # Blend AI score: 60% heuristic + 40% AI
                blended = int(score * 0.6 + ai_review.get("ai_score", score) * 0.4)
                ai_review["blended_score"] = blended
                score = blended
                status = "Aprovado" if score >= 70 else "Reprovado"
            except Exception as e:
                ai_review = {"error": str(e)}

        result = {
            "filename": filename,
            "score": score,
            "status": status,
            "word_count": word_count,
            "h2_count": h2_count,
            "h3_count": h3_count,
            "internal_links": internal_links,
            "external_links": external_links,
            "images": images,
            "issues": issues,
            "warnings": warnings,
            "ai_review": ai_review,
            "verified_at": datetime.now().isoformat(),
        }

        history = _load_json("verify_history.json", [])
        history.append(result)
        history = history[-50:]
        _save_json("verify_history.json", history)

        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/verify/history/delete/<int:index>", methods=["DELETE"])
@login_required
def api_delete_verify_history(index):
    try:
        history = _load_json("verify_history.json", [])
        if index < 0 or index >= len(history):
            return jsonify({"success": False, "error": f"Índice inválido: {index}"}), 404
        removed = history.pop(index)
        _save_json("verify_history.json", history)
        return jsonify({"success": True, "deleted": removed})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
#  API: Generate image
# ---------------------------------------------------------------------------

@app.route("/api/images/generate", methods=["POST"])
@login_required
def api_generate_image():
    try:
        data = request.json or {}
        prompt = data.get("prompt", "").strip()
        filename = data.get("filename", "pin.png")
        usage = data.get("usage", "square")
        if not prompt:
            return jsonify({"success": False, "error": "Prompt obrigatório"}), 400

        api_key = _env("GEMINI_API_KEY")
        image_bytes, provider = generate_image(prompt=prompt, api_key=api_key, usage=usage)

        images_dir = Path(app.root_path) / "static" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / filename).write_bytes(image_bytes)

        return jsonify({
            "success": True, "filename": filename,
            "size_kb": round(len(image_bytes) / 1024, 1), "provider": provider,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/images/generate_pin", methods=["POST"])
@login_required
def api_generate_pin_for_article():
    try:
        data = request.json or {}
        filename = data.get("filename", "").strip()
        usage = data.get("usage", "pinterest")
        if not filename:
            return jsonify({"success": False, "error": "Arquivo obrigatório"}), 400

        filepath = _articles_dir() / filename
        if not filepath.exists():
            return jsonify({"success": False, "error": f"Arquivo não encontrado: {filename}"}), 404

        article_info = _extract_article_info(filepath)
        prompt = data.get("prompt", "") or _build_pin_prompt(article_info, usage=usage)
        slug = extract_slug_from_filename(filename)
        pin_filename = f"pin-{slug}.png"

        api_key = _env("GEMINI_API_KEY")
        image_bytes, provider = generate_image(prompt=prompt, api_key=api_key, usage=usage)

        images_dir = Path(app.root_path) / "static" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / pin_filename).write_bytes(image_bytes)

        return jsonify({
            "success": True, "filename": pin_filename, "article": filename,
            "title": article_info["title"], "description": article_info["meta_description"],
            "slug": article_info["slug"], "tags": article_info["tags"],
            "excerpt": article_info["excerpt"],
            "size_kb": round(len(image_bytes) / 1024, 1),
            "url": f"/static/images/{pin_filename}",
            "prompt_used": prompt, "provider": provider,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/images/list")
@login_required
def api_list_images():
    images_dir = Path(app.root_path) / "static" / "images"
    images = []
    if images_dir.exists():
        for f in sorted(images_dir.glob("*.png"), reverse=True):
            images.append({
                "filename": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
                "is_pin": f.name.startswith("pin-"),
            })
    return jsonify(images)


@app.route("/api/images/delete/<filename>", methods=["DELETE"])
@login_required
def api_delete_image(filename):
    try:
        images_dir = Path(app.root_path) / "static" / "images"
        filepath = images_dir / filename
        if not filepath.exists():
            return jsonify({"success": False, "error": f"Imagem não encontrada: {filename}"}), 404
        filepath.unlink()
        return jsonify({"success": True, "filename": filename})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/images/pin_info/<filename>")
@login_required
def api_pin_info(filename: str):
    slug = filename.replace("pin-", "").replace(".png", "")
    for f in _articles_dir().glob("*.md"):
        if extract_slug_from_filename(f.name) == slug:
            info = _extract_article_info(f)
            site_url = _env("SITE_URL", "https://tech-tips.byethost4.com")
            return jsonify({
                "success": True,
                "title": info["title"], "description": info["meta_description"],
                "excerpt": info["excerpt"], "tags": info["tags"],
                "link": f"{site_url}/{info['slug']}/", "article_file": f.name,
            })
    return jsonify({"success": False, "error": "Artigo não encontrado"})


# ---------------------------------------------------------------------------
#  API: Pipeline (unified)
# ---------------------------------------------------------------------------

@app.route("/api/pipeline", methods=["POST"])
@login_required
def api_pipeline():
    try:
        data = request.json or {}
        keyword = data.get("keyword", "").strip()
        if not keyword:
            return jsonify({"success": False, "error": "Palavra-chave obrigatória"}), 400

        result = _run_pipeline_logic(
            keyword=keyword,
            pin_prompt=data.get("pin_prompt", ""),
            skip_publish=data.get("skip_publish", False),
            skip_pinterest=data.get("skip_pinterest", False),
            article_filename=data.get("article_filename", ""),
            force_restart=data.get("force_restart", False),
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/pipeline/history")
@login_required
def api_pipeline_history():
    history = _load_json("pipeline_history.json", [])
    if not isinstance(history, list):
        history = []
    history.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
    return jsonify(history)


@app.route("/api/pipeline/history/delete/<int:index>", methods=["DELETE"])
@login_required
def api_delete_pipeline_history(index):
    try:
        history = _load_json("pipeline_history.json", [])
        if not isinstance(history, list):
            return jsonify({"success": False, "error": "Histórico inválido"}), 500
        if index < 0 or index >= len(history):
            return jsonify({"success": False, "error": f"Índice inválido: {index}"}), 404
        removed = history.pop(index)
        _save_json("pipeline_history.json", history)
        return jsonify({"success": True, "deleted": removed})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/pipeline/checkpoints")
@login_required
def api_pipeline_checkpoints():
    return jsonify(_load_checkpoints())


@app.route("/api/pipeline/checkpoints/clear/<slug>", methods=["DELETE"])
@login_required
def api_clear_checkpoint(slug):
    try:
        _clear_checkpoint(slug)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
#  API: Publish (REST API — unified)
# ---------------------------------------------------------------------------

@app.route("/api/publish", methods=["POST"])
@login_required
def api_publish():
    try:
        data = request.json or {}
        filename = data.get("filename", "").strip()
        if not filename:
            return jsonify({"success": False, "error": "Arquivo obrigatório"}), 400

        filepath = _articles_dir() / filename
        if not filepath.exists():
            return jsonify({"success": False, "error": f"Arquivo não encontrado: {filename}"}), 404

        info = _extract_article_info(filepath)
        article_data = {
            "title": info["title"],
            "content": info["body_text"],
            "slug": info["slug"],
            "meta_description": info["meta_description"],
        }

        result = _wp_publish(article_data, status=data.get("status", "publish"))
        if result["success"]:
            return jsonify({"success": True, "post_id": result.get("id"), "url": result.get("link")})
        return jsonify({"success": False, "error": result["error"]}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
#  API: Pinterest
# ---------------------------------------------------------------------------

@app.route("/api/pinterest/create", methods=["POST"])
@login_required
def api_pinterest_create():
    try:
        import httpx as _httpx
        data = request.json or {}
        access_token = _env("PINTEREST_ACCESS_TOKEN") or _load_json("pinterest_config.json", {}).get("access_token", "")
        board_id = _env("PINTEREST_BOARD_ID") or _load_json("pinterest_config.json", {}).get("board_id", "")
        if not access_token or not board_id:
            return jsonify({"success": False, "error": "Pinterest não configurado."})

        payload = {
            "board_id": board_id,
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "link": data.get("link", _env("SITE_URL", "https://tech-tips.byethost4.com")),
        }
        image_url = data.get("image_url", "")
        # Convert local URLs to public (WP media or Pollinations fallback)
        if image_url and ("localhost" in image_url or image_url.startswith("/static/")):
            # Try to upload to WordPress to get a public URL
            try:
                import base64 as _b64
                # Extract filename from URL
                img_filename = image_url.split("/")[-1]
                img_path = Path(app.root_path) / "static" / "images" / img_filename
                if img_path.exists():
                    wp_result = _wp_upload_media(img_path.read_bytes(), img_filename, alt_text=data.get("title", ""))
                    if wp_result["success"]:
                        image_url = wp_result["url"]
                    else:
                        # Fallback: use Pollinations URL
                        image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(data.get('title', 'blog post'))}?width=768&height=1024&nologo=true"
            except Exception:
                image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(data.get('title', 'blog post'))}?width=768&height=1024&nologo=true"
        if image_url:
            payload["image_source_url"] = image_url

        resp = _httpx.post(
            "https://api.pinterest.com/v5/pins",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        if resp.status_code in (200, 201):
            pin = resp.json()
            config = _load_json("pinterest_config.json", {})
            published = config.get("published_pins", [])
            published.append({"pin_id": pin.get("id", ""), "title": data.get("title", ""),
                               "created_at": datetime.now().isoformat()})
            config["published_pins"] = published[-50:]
            _save_json("pinterest_config.json", config)
            return jsonify({"success": True, "pin_id": pin.get("id"), "url": pin.get("link")})
        return jsonify({"success": False, "error": f"Erro Pinterest API: {resp.status_code} - {resp.text[:200]}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/pinterest/list")
@login_required
def api_pinterest_list():
    return jsonify(_load_json("pinterest_config.json", {}))


# ---------------------------------------------------------------------------
#  API: AdCash stats (real API)
# ---------------------------------------------------------------------------

@app.route("/api/adcash")
@login_required
def api_adcash():
    return jsonify(_load_json("adcash_stats.json", {}))


@app.route("/api/adcash/refresh", methods=["POST"])
@login_required
def api_adcash_refresh():
    """Fetch real stats from AdCash Publisher API."""
    try:
        import httpx as _httpx

        config = _load_json("adcash_config.json", {})
        token = _env("ADCASH_API_TOKEN") or config.get("api_token", "")
        zone_id = _env("ADCASH_ZONE_ID") or config.get("zone_id", "")

        if not token:
            return jsonify({"success": False, "error": "Token AdCash não configurado. Adicione ADCASH_API_TOKEN em Config."})

        stats = _load_json("adcash_stats.json", {})

        # AdCash Publisher Stats API
        # Docs: https://publisher.adcash.com/docs/api
        today = datetime.now().strftime("%Y-%m-%d")
        month_start = datetime.now().strftime("%Y-%m-01")

        try:
            resp = _httpx.get(
                "https://publisher.adcash.com/api/v2/stats",
                params={
                    "date_from": month_start,
                    "date_to": today,
                    "group_by": "day",
                    "zone_id": zone_id,
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            if resp.status_code == 200:
                api_data = resp.json()
                rows = api_data.get("data", api_data.get("rows", []))

                total_revenue = sum(float(r.get("revenue", r.get("earnings", 0))) for r in rows)
                total_impressions = sum(int(r.get("impressions", 0)) for r in rows)
                total_clicks = sum(int(r.get("clicks", 0)) for r in rows)
                avg_ecpm = (total_revenue / total_impressions * 1000) if total_impressions > 0 else 0

                # Build daily stats list
                daily_stats = []
                for row in rows:
                    daily_stats.append({
                        "date": row.get("date", row.get("day", "")),
                        "impressions": int(row.get("impressions", 0)),
                        "clicks": int(row.get("clicks", 0)),
                        "revenue": float(row.get("revenue", row.get("earnings", 0))),
                        "ecpm": float(row.get("ecpm", 0)),
                    })

                stats.update({
                    "total_revenue": round(total_revenue, 4),
                    "total_impressions": total_impressions,
                    "total_clicks": total_clicks,
                    "avg_ecpm": round(avg_ecpm, 2),
                    "daily_stats": daily_stats,
                    "last_updated": datetime.now().isoformat(),
                    "api_status": "ok",
                })
            else:
                # API responded but not 200 — store error detail
                stats["last_updated"] = datetime.now().isoformat()
                stats["api_status"] = f"error_{resp.status_code}"
                stats["api_error"] = resp.text[:200]
        except Exception as api_err:
            stats["last_updated"] = datetime.now().isoformat()
            stats["api_status"] = "unreachable"
            stats["api_error"] = str(api_err)

        _save_json("adcash_stats.json", stats)
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
#  API: Scheduler (APScheduler)
# ---------------------------------------------------------------------------

@app.route("/api/scheduler/status")
@login_required
def api_scheduler_status():
    if not _SCHEDULER_AVAILABLE or not _scheduler:
        return jsonify({"available": False, "error": "APScheduler não instalado"})
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return jsonify({"available": True, "running": _scheduler.running, "jobs": jobs})


@app.route("/api/scheduler/add", methods=["POST"])
@login_required
def api_scheduler_add():
    """Add a scheduled pipeline job. Body: {keyword, hour, minute, days_of_week}."""
    if not _SCHEDULER_AVAILABLE or not _scheduler:
        return jsonify({"success": False, "error": "APScheduler não disponível"}), 503
    try:
        data = request.json or {}
        keyword = data.get("keyword", "").strip()
        hour = int(data.get("hour", 8))
        minute = int(data.get("minute", 0))
        days = data.get("days_of_week", "mon-sun")  # e.g. "mon,wed,fri" or "mon-sun"

        if not keyword:
            return jsonify({"success": False, "error": "Palavra-chave obrigatória"}), 400

        job_id = f"pipeline_{re.sub(r'[^a-z0-9]', '_', keyword.lower()[:30])}_{hour:02d}{minute:02d}"

        # Remove existing job with same id if present
        try:
            _scheduler.remove_job(job_id)
        except Exception:
            pass

        _scheduler.add_job(
            _scheduled_pipeline_job,
            trigger=CronTrigger(day_of_week=days, hour=hour, minute=minute),
            args=[keyword],
            id=job_id,
            name=f"Pipeline: {keyword[:40]}",
            replace_existing=True,
        )

        # Persist to JSON so jobs survive restarts
        sched_data = _load_json("scheduler_jobs.json", [])
        sched_data = [j for j in sched_data if j.get("id") != job_id]  # remove dupe
        sched_data.append({
            "id": job_id, "keyword": keyword,
            "hour": hour, "minute": minute, "days": days,
            "created_at": datetime.now().isoformat(),
        })
        _save_json("scheduler_jobs.json", sched_data)

        job = _scheduler.get_job(job_id)
        return jsonify({
            "success": True,
            "job_id": job_id,
            "next_run": str(job.next_run_time) if job and job.next_run_time else None,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scheduler/remove/<job_id>", methods=["DELETE"])
@login_required
def api_scheduler_remove(job_id):
    if not _SCHEDULER_AVAILABLE or not _scheduler:
        return jsonify({"success": False, "error": "APScheduler não disponível"}), 503
    try:
        _scheduler.remove_job(job_id)
    except Exception:
        pass
    sched_data = _load_json("scheduler_jobs.json", [])
    sched_data = [j for j in sched_data if j.get("id") != job_id]
    _save_json("scheduler_jobs.json", sched_data)
    return jsonify({"success": True})


@app.route("/api/scheduler/run_now/<job_id>", methods=["POST"])
@login_required
def api_scheduler_run_now(job_id):
    """Trigger a scheduled job immediately."""
    if not _SCHEDULER_AVAILABLE or not _scheduler:
        return jsonify({"success": False, "error": "APScheduler não disponível"}), 503
    try:
        sched_data = _load_json("scheduler_jobs.json", [])
        job_cfg = next((j for j in sched_data if j.get("id") == job_id), None)
        if not job_cfg:
            return jsonify({"success": False, "error": "Job não encontrado"}), 404
        _scheduler.add_job(
            _scheduled_pipeline_job,
            args=[job_cfg["keyword"]],
            id=f"{job_id}_manual_{int(datetime.now().timestamp())}",
            name=f"Manual: {job_cfg['keyword'][:40]}",
        )
        return jsonify({"success": True, "message": f"Executando agora: {job_cfg['keyword']}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _restore_scheduler_jobs():
    """Re-register persisted jobs after server restart."""
    if not _SCHEDULER_AVAILABLE or not _scheduler:
        return
    sched_data = _load_json("scheduler_jobs.json", [])
    for job_cfg in sched_data:
        try:
            _scheduler.add_job(
                _scheduled_pipeline_job,
                trigger=CronTrigger(
                    day_of_week=job_cfg.get("days", "mon-sun"),
                    hour=int(job_cfg.get("hour", 8)),
                    minute=int(job_cfg.get("minute", 0)),
                ),
                args=[job_cfg["keyword"]],
                id=job_cfg["id"],
                name=f"Pipeline: {job_cfg['keyword'][:40]}",
                replace_existing=True,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
#  API: Settings
# ---------------------------------------------------------------------------

@app.route("/api/settings", methods=["GET"])
@login_required
def api_settings_get():
    env = _load_env_dict()
    masked = {}
    for k, v in env.items():
        if any(s in k for s in ["PASS", "SECRET", "TOKEN", "KEY"]):
            masked[k] = v[:4] + "..." + v[-4:] if len(v) > 8 else "***"
        else:
            masked[k] = v
    return jsonify(masked)


def _is_masked(value: str) -> bool:
    """Return True if the value looks like a masked secret (should not be saved)."""
    if not value:
        return False
    # Patterns: "AQ.A...MZ3Q", "xxxx...yyyy", "***", "AIza...abcd"
    if "..." in value:
        return True
    if value == "***":
        return True
    # Value ends with '...' (old pattern)
    if value.endswith("..."):
        return True
    return False


@app.route("/api/settings", methods=["POST"])
@login_required
def api_settings_save():
    try:
        data = request.json
        env = _load_env_dict()
        skipped = []
        for k, v in data.items():
            if not k:
                continue
            v = (v or "").strip()
            if not v:
                continue
            if _is_masked(v):
                skipped.append(k)
                continue
            env[k] = v
        _save_env_dict(env)
        for k, v in env.items():
            os.environ[k] = v
        result = {"success": True}
        if skipped:
            result["skipped"] = skipped
            result["warning"] = f"Valores mascarados não foram salvos: {', '.join(skipped)}"
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/settings/test_wp", methods=["POST"])
@login_required
def api_test_wp():
    try:
        import httpx as _httpx
        env = _load_env_dict()
        site_url = env.get("SITE_URL", "https://tech-tips.byethost4.com")
        wp_user = env.get("WP_USER", "")
        wp_pass = env.get("WP_APP_PASSWORD", "")
        if not wp_user or not wp_pass:
            return jsonify({"success": False, "error": "Configure WP_USER e WP_APP_PASSWORD"})
        resp = _httpx.get(f"{site_url}/wp-json/wp/v2/users/me",
                          auth=(wp_user, wp_pass), timeout=10, verify=False)
        if resp.status_code == 200:
            user = resp.json()
            return jsonify({"success": True, "message": f"Conectado como: {user.get('name', 'Unknown')}"})
        return jsonify({"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
#  Generic script runner (legacy)
# ---------------------------------------------------------------------------

@app.route("/api/run_script", methods=["POST"])
@login_required
def api_run_script():
    try:
        data = request.json
        script_name = data.get("script_name", "")
        args = data.get("args", [])
        if not script_name:
            return jsonify({"success": False, "error": "script_name obrigatório"}), 400

        script_path = _scripts_dir() / script_name
        if not script_path.exists():
            return jsonify({"success": False, "error": f"Script não encontrado: {script_name}"})

        venv_python = Path(app.root_path).parent / "venv" / "bin" / "python"
        python_bin = str(venv_python) if venv_python.exists() else sys.executable

        env = os.environ.copy()
        env.update(_load_env_dict())

        result = subprocess.run(
            [python_bin, str(script_path)] + args,
            env=env, capture_output=True, text=True, timeout=300,
        )
        return jsonify({
            "success": result.returncode == 0,
            "output": result.stdout + "\n" + result.stderr,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "output": "Timeout: script demorou mais de 5 minutos"})
    except Exception as e:
        return jsonify({"success": False, "output": str(e)})


# ---------------------------------------------------------------------------
#  Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    env_path = Path(app.root_path).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

    # Set secret key from env if available
    app.secret_key = os.environ.get(
        "FLASK_SECRET_KEY",
        hashlib.sha256(os.environ.get("DASHBOARD_PASSWORD", "blog-dolar").encode()).hexdigest()
    )

    # Restore scheduled jobs from persistence
    _restore_scheduler_jobs()

    app.run(debug=True, host="0.0.0.0", port=5001)
