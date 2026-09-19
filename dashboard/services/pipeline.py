# -*- coding: utf-8 -*-
"""Pipeline automation and checkpoint services."""
import json
import re
import urllib.parse
from datetime import datetime
from pathlib import Path

import httpx

from dashboard.services.articles import _extract_article_info
from dashboard.services.bridge import get_bridge_url, is_bridge_enabled
from dashboard.services.gemini import _gemini_call
from dashboard.services.helpers import (
    _articles_dir,
    _data_path,
    _env,
    _images_dir,
    _parse_json,
)
from dashboard.services.images import _build_pin_prompt
from dashboard.services.wordpress import _wp_publish, _wp_upload_media
from db import (
    clear_checkpoints as db_clear_checkpoints,
    get_checkpoint as db_get_checkpoint,
    get_config,
    get_pipeline_history,
    save_checkpoint as db_save_checkpoint,
    save_config,
    save_pipeline_history,
)
from image_generator import (
    build_pin_description,
    extract_slug_from_filename,
    generate_image,
    generate_pin_title,
)


# ---------------------------------------------------------------------------
#  Pipeline Checkpoint Helpers (JSON fallback + DB sync)
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
    # Save to local JSON
    checkpoints = _load_checkpoints()
    if slug not in checkpoints:
        checkpoints[slug] = {}
    checkpoints[slug][step] = value
    checkpoints[slug]["updated_at"] = datetime.now().isoformat()
    _checkpoint_path().parent.mkdir(parents=True, exist_ok=True)
    _checkpoint_path().write_text(json.dumps(checkpoints, indent=2, ensure_ascii=False), encoding="utf-8")

    # Sync to DB
    try:
        db_save_checkpoint(slug, step, value)
    except Exception:
        pass


def _get_checkpoint(slug: str, step: str):
    val = _load_checkpoints().get(slug, {}).get(step)
    if val is not None:
        return val
    try:
        return db_get_checkpoint(slug, step)
    except Exception:
        return None


def _clear_checkpoint(slug: str):
    checkpoints = _load_checkpoints()
    checkpoints.pop(slug, None)
    try:
        _checkpoint_path().write_text(json.dumps(checkpoints, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    try:
        db_clear_checkpoints(slug)
    except Exception:
        pass


# ---------------------------------------------------------------------------
#  Scheduled Pipeline Job
# ---------------------------------------------------------------------------

def _scheduled_pipeline_job(keyword: str):
    """Run the full pipeline for a keyword (called by APScheduler)."""
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
        save_pipeline_history({
            "keyword": keyword,
            "article": "",
            "title": keyword,
            "image": "",
            "image_url": "",
            "post_url": "",
            "steps": [{"step": "scheduler", "status": "error", "error": str(e)}],
            "completed_at": datetime.now().isoformat(),
        })


# ---------------------------------------------------------------------------
#  Core Pipeline Logic
# ---------------------------------------------------------------------------

def _run_pipeline_logic(keyword: str, pin_prompt: str = "", skip_publish: bool = False,
                        skip_pinterest: bool = False, article_filename: str = "",
                        force_restart: bool = False) -> dict:
    """Execute the full pipeline: Article -> Image -> WordPress -> Pinterest."""
    steps = []
    pipeline_slug = re.sub(r'[^a-z0-9-]', '-', keyword.lower().strip())[:60]
    site_url = _env("SITE_URL", "https://tech-tips.ct.ws")

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
            steps.append({
                "step": "article",
                "status": "ok",
                "filename": article_filename,
                "title": title,
                "from_checkpoint": True,
            })
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
    images_dir = _images_dir()
    public_image_url = ""

    # Check checkpoint for image
    ckpt_image = _get_checkpoint(pipeline_slug, "image") if not force_restart else None
    if ckpt_image and (images_dir / ckpt_image).exists():
        pin_filename = ckpt_image
        image_bytes = (images_dir / pin_filename).read_bytes()
        provider = "checkpoint"
        try:
            wp_ckpt = _wp_upload_media(image_bytes, pin_filename, alt_text=title or pin_filename)
            if wp_ckpt.get("success"):
                public_image_url = wp_ckpt["url"]
        except Exception:
            pass
        steps.append({
            "step": "image",
            "status": "ok",
            "filename": pin_filename,
            "size_kb": round(len(image_bytes) / 1024, 1),
            "provider": provider,
            "from_checkpoint": True,
        })
    else:
        article_info = _extract_article_info(filepath)
        if not pin_prompt:
            pin_prompt = _build_pin_prompt(article_info, usage="pinterest")
        api_key_img = _env("GEMINI_API_KEY")
        image_bytes, provider = generate_image(prompt=pin_prompt, api_key=api_key_img, usage="pinterest")
        (images_dir / pin_filename).write_bytes(image_bytes)
        # Best-effort featured image
        try:
            feat_prompt = _build_pin_prompt(article_info, usage="featured")
            featured_bytes, _ = generate_image(prompt=feat_prompt, api_key=api_key_img, usage="featured")
            (images_dir / f"featured-{image_slug}.png").write_bytes(featured_bytes)
        except Exception:
            pass
        _save_checkpoint(pipeline_slug, "image", pin_filename)
        try:
            wp_media = _wp_upload_media(image_bytes, pin_filename, alt_text=title or pin_filename)
            if wp_media.get("success"):
                public_image_url = wp_media["url"]
        except Exception:
            pass
        steps.append({
            "step": "image",
            "status": "ok",
            "filename": pin_filename,
            "size_kb": round(len(image_bytes) / 1024, 1),
            "provider": provider,
        })

    # ---- Step 3: WordPress Publish ----
    post_url = ""
    if not skip_publish:
        ckpt_publish = _get_checkpoint(pipeline_slug, "publish") if not force_restart else None
        if ckpt_publish:
            post_url = ckpt_publish.get("url", "")
            public_image_url = ckpt_publish.get("image_url", "")
            steps.append({
                "step": "publish",
                "status": "ok",
                "post_id": ckpt_publish.get("post_id"),
                "url": post_url,
                "from_checkpoint": True,
            })
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

                feat_path = images_dir / f"featured-{image_slug}.png"
                if feat_path.exists():
                    media_result = _wp_upload_media(
                        feat_path.read_bytes(),
                        f"featured-{image_slug}.png",
                        alt_text=title,
                    )
                    if media_result.get("success"):
                        article_data["featured_media_id"] = media_result["id"]
                        public_image_url = media_result["url"]

                if not public_image_url:
                    pin_path = images_dir / pin_filename
                    if pin_path.exists():
                        pin_media = _wp_upload_media(
                            pin_path.read_bytes(),
                            pin_filename,
                            alt_text=title,
                        )
                        if pin_media.get("success"):
                            public_image_url = pin_media["url"]

                if not public_image_url:
                    encoded_prompt = urllib.parse.quote(f"professional, high quality, {title}")
                    public_image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=675&nologo=true"

                if public_image_url:
                    body = f"![{title}]({public_image_url})\n\n" + body
                    article_data["content"] = body
                    if file_content.startswith("---") and len(file_content.split("---", 2)) >= 3:
                        parts = file_content.split("---", 2)
                        new_file_content = f"---{parts[1]}---\n{body}"
                    else:
                        new_file_content = body
                    filepath.write_text(new_file_content, encoding="utf-8")

                pub_result = _wp_publish(article_data, status="publish")
                if pub_result.get("success"):
                    post_url = pub_result.get("link", "")
                    _save_checkpoint(pipeline_slug, "publish", {
                        "post_id": pub_result.get("id"),
                        "url": post_url,
                        "image_url": public_image_url,
                    })
                    steps[-1] = {"step": "publish", "status": "ok", "post_id": pub_result.get("id"), "url": post_url}
                else:
                    steps[-1] = {"step": "publish", "status": "error", "error": pub_result.get("error", "Erro ao publicar")}
            except Exception as e:
                steps[-1] = {"step": "publish", "status": "error", "error": str(e)}
    else:
        steps.append({"step": "publish", "status": "skipped"})

    if not public_image_url:
        public_image_url = (
            f"https://image.pollinations.ai/prompt/"
            f"{urllib.parse.quote(pin_prompt or title)}?width=768&height=1024&nologo=true"
        )

    # ---- Step 4: Pinterest ----
    if not skip_pinterest:
        ckpt_pin = _get_checkpoint(pipeline_slug, "pinterest") if not force_restart else None
        if ckpt_pin:
            steps.append({"step": "pinterest", "status": "ok", "pin_id": ckpt_pin, "from_checkpoint": True})
        else:
            steps.append({"step": "pinterest", "status": "running"})
            try:
                access_token = _env("PINTEREST_ACCESS_TOKEN") or get_config("pinterest_config", {}).get("access_token", "")
                board_id = _env("PINTEREST_BOARD_ID") or get_config("pinterest_config", {}).get("board_id", "")
                if not access_token or not board_id:
                    steps[-1] = {"step": "pinterest", "status": "error",
                                 "error": "Pinterest não configurado (ACCESS_TOKEN ou BOARD_ID ausente)"}
                else:
                    image_step = next((s for s in steps if s.get("step") == "image"), {})
                    pin_files = image_step.get("files", [pin_filename])

                    # Ensure public_image_url is on WP domain if possible
                    if not public_image_url or site_url not in public_image_url:
                        main_pin_path = images_dir / pin_filename
                        if main_pin_path.exists():
                            wp_media = _wp_upload_media(main_pin_path.read_bytes(), pin_filename, alt_text=title)
                            if wp_media.get("success"):
                                public_image_url = wp_media["url"]

                    pin_ids = []
                    for pf in pin_files:
                        pf_path = images_dir / pf
                        if not pf_path.exists():
                            continue
                        pf_media = _wp_upload_media(pf_path.read_bytes(), pf, alt_text=title)
                        pf_url = pf_media.get("url", public_image_url) if pf_media.get("success") else public_image_url

                        pin_api_key = _env("GEMINI_API_KEY")
                        excerpt_clean = re.sub(r'<[^>]+>', '', meta_desc or title)
                        pin_title = generate_pin_title(pin_api_key, title, excerpt_clean) if pin_api_key else title
                        pin_desc = build_pin_description(
                            pin_api_key, title, excerpt_clean,
                            keywords=article_info.get("keywords") if 'article_info' in locals() else None,
                            tags=article_info.get("tags") if 'article_info' in locals() else None,
                        ) if pin_api_key else (meta_desc or f"Read about {title}")

                        bridge_url = get_bridge_url(slug, post_url) if is_bridge_enabled() else ""
                        pin_target_link = bridge_url or post_url or site_url

                        pin_payload = {
                            "board_id": board_id,
                            "title": pin_title[:100],
                            "description": pin_desc[:500],
                            "link": pin_target_link,
                            "image_source_url": pf_url,
                        }
                        resp_pin = httpx.post(
                            "https://api.pinterest.com/v5/pins",
                            json=pin_payload,
                            headers=({"Authorization": f"Bearer {access_token}"}
                                     if not access_token.startswith("Bearer ")
                                     else {"Authorization": access_token}),
                            timeout=30,
                        )
                        if resp_pin.status_code in (401, 403):
                            steps[-1] = {
                                "step": "pinterest",
                                "status": "error",
                                "error": f"Token expirado ({resp_pin.status_code}). Configure PINTEREST_ACCESS_TOKEN.",
                            }
                            break
                        if resp_pin.status_code in (200, 201):
                            pin_data = resp_pin.json()
                            pin_id = pin_data.get("id", "")
                            pin_ids.append(pin_id)
                            config = get_config("pinterest_config", {})
                            published = config.get("published_pins", [])
                            published.append({
                                "pin_id": pin_id,
                                "title": title,
                                "article": article_filename,
                                "created_at": datetime.now().isoformat(),
                            })
                            config["published_pins"] = published[-50:]
                            save_config("pinterest_config", config)
                            _save_checkpoint(pipeline_slug, "pinterest", pin_id)
                            steps[-1] = {"step": "pinterest", "status": "ok", "pin_id": pin_id}
                        else:
                            steps[-1] = {
                                "step": "pinterest",
                                "status": "error",
                                "error": f"HTTP {resp_pin.status_code}: {resp_pin.text[:200]}",
                            }
                            break
                    if pin_ids:
                        steps[-1] = {"step": "pinterest", "status": "ok", "pin_ids": pin_ids, "count": len(pin_ids)}
            except Exception as e:
                steps[-1] = {"step": "pinterest", "status": "error", "error": str(e)}
    else:
        steps.append({"step": "pinterest", "status": "skipped"})

    bridge_url = get_bridge_url(slug, post_url) if is_bridge_enabled() else ""

    # Save execution to history
    save_pipeline_history({
        "keyword": keyword,
        "article": article_filename,
        "title": title,
        "image": pin_filename,
        "image_url": public_image_url,
        "post_url": post_url,
        "bridge_url": bridge_url,
        "steps": steps,
        "completed_at": datetime.now().isoformat(),
    })

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
        "bridge_url": bridge_url,
        "steps": steps,
    }

