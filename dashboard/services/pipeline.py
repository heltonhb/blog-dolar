# -*- coding: utf-8 -*-
"""Pipeline automation and checkpoint services."""
import json
import logging
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


log = logging.getLogger("dashboard.pipeline")


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
        # The JSON copy is authoritative for resume; a DB sync failure must not
        # abort the pipeline, but it must be visible when debugging.
        log.debug("checkpoint não sincronizado com o Postgres (slug=%s step=%s)", slug, step, exc_info=True)


def _get_checkpoint(slug: str, step: str):
    val = _load_checkpoints().get(slug, {}).get(step)
    if val is not None:
        return val
    try:
        return db_get_checkpoint(slug, step)
    except Exception:
        # JSON was the miss; falling back to None just means "not done yet".
        log.debug("checkpoint ausente no Postgres (slug=%s step=%s)", slug, step, exc_info=True)
        return None


def _clear_checkpoint(slug: str):
    checkpoints = _load_checkpoints()
    checkpoints.pop(slug, None)
    try:
        _checkpoint_path().write_text(json.dumps(checkpoints, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        log.warning("não foi possível gravar checkpoints limpos em disco", exc_info=True)
    try:
        db_clear_checkpoints(slug)
    except Exception:
        log.debug("checkpoint não removido do Postgres (slug=%s)", slug, exc_info=True)


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


def _scheduled_pinterest_drip_job(board_id: str = ""):
    """Publish the next pending pin in the drip-feed queue (called by APScheduler)."""
    try:
        from dashboard.services.pinterest_queue import publish_next_pin

        res = publish_next_pin(board_id=board_id or None)
        log.info("Pinterest drip-feed job concluído: %s", res)
        return res
    except Exception as e:
        log.exception("Pinterest drip-feed job falhou: %s", e)
        return {"success": False, "error": str(e)}


def _scheduled_autopilot_job(category: str = "buyer_intent"):
    """Run an automated monetization autopilot cycle (called by APScheduler)."""
    try:
        log.info("Iniciando scheduled autopilot job (category=%s)", category)
        res = run_autopilot_cycle(category_filter=category)
        log.info("Scheduled autopilot job finalizado: success=%s", res.get("success"))
        return res
    except Exception as e:
        log.exception("Scheduled autopilot job falhou: %s", e)
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
#  Core Pipeline Logic
# ---------------------------------------------------------------------------

def _run_pipeline_logic(keyword: str, pin_prompt: str = "", skip_publish: bool = False,
                        skip_pinterest: bool = False, article_filename: str = "",
                        force_restart: bool = False) -> dict:
    """Execute the full pipeline: Article -> Image -> WordPress -> Pinterest."""
    steps = []
    pipeline_slug = re.sub(r'[^a-z0-9-]', '-', keyword.lower().strip())[:60]
    site_url = _env("SITE_URL", "https://techtips.dpdns.org")

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
- Recommend 3 to 5 real, popular products from Amazon US relevant to this topic for reader recommendations

Return ONLY JSON:
{{
  "title": "SEO title",
  "slug": "url-friendly-slug",
  "meta_description": "...",
  "content": "Full HTML article with <h2>, <h3>, <p>, <ul>, <table> tags",
  "tags": ["tag1", "tag2", "tag3"],
  "products": [
    {{
      "title": "Exact Product Name",
      "subtitle": "Short 1-sentence value proposition or why it is recommended",
      "search_query": "Amazon search query for this product",
      "badge": "e.g. BEST OVERALL, BEST VALUE, or TOP PICK",
      "after_heading": "Exact heading or phrase in the article where this product belongs",
      "specs": ["Key feature 1", "Key feature 2", "Key feature 3"]
    }}
  ]
}}"""
            result = _gemini_call(prompt)
            article = _parse_json(result)
            articles_dir = _articles_dir()
            articles_dir.mkdir(exist_ok=True)
            date_str = datetime.now().strftime("%Y-%m-%d")
            slug = article.get("slug", "untitled")
            article_filename = f"{date_str}_{slug}.md"
            filepath = articles_dir / article_filename

            products = article.get("products", [])
            if products and isinstance(products, list):
                try:
                    from scripts.affiliate_manager import save_custom_products
                except ImportError:
                    try:
                        from affiliate_manager import save_custom_products
                    except Exception:
                        save_custom_products = None
                if save_custom_products:
                    try:
                        save_custom_products(slug, products)
                    except Exception:
                        pass

            products_yaml = f"\nproducts: {json.dumps(products)}" if products else ""
            file_content = (
                f"---\ntitle: {article.get('title', 'Untitled')}\ndate: {date_str}\n"
                f"slug: {slug}\nmeta_description: {article.get('meta_description', '')}\n"
                f"tags: {json.dumps(article.get('tags', []))}{products_yaml}\n---\n\n{article.get('content', '')}\n"
            )
            filepath.write_text(file_content, encoding="utf-8")
            title = article.get("title", keyword)
            meta_desc = article.get("meta_description", "")
            _save_checkpoint(pipeline_slug, "article", article_filename)
            steps[-1] = {
                "step": "article",
                "status": "ok",
                "filename": article_filename,
                "title": title,
                "products_count": len(products) if isinstance(products, list) else 0,
            }

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
                    try:
                        from dashboard.services.post_hooks import trigger_post_publish_tasks
                        trigger_post_publish_tasks(article_data["slug"], post_id=pub_result.get("id"))
                    except Exception:
                        pass
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
                    steps[-1] = {
                        "step": "pinterest",
                        "status": "ok",
                        "queued": True,
                        "message": "Pins salvos na fila Drip-Feed (API v5 direta não configurada)",
                    }
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
                                "status": "ok",
                                "queued": True,
                                "warning": f"Token Pinterest expirado ({resp_pin.status_code}). Pins salvos na fila Drip-Feed para agendamento.",
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


def run_autopilot_cycle(
    idea_id: int | None = None,
    category_filter: str = "buyer_intent",
    skip_publish: bool = False,
    skip_pinterest: bool = False,
    force_restart: bool = False,
) -> dict:
    """Run an automated monetization autopilot cycle (Automação 5 / Fase 4).

    1. Selects the next pending buyer_intent idea (or specific idea_id).
    2. Writes commercial article with Gemini, extracting Amazon products.
    3. Injects Quick Recommendations + Amazon affiliate cards (heltonhb-20).
    4. Publishes to WordPress with featured image.
    5. Triggers post-hooks: 3 vertical Pinterest pins + cross-interlinking.
    6. Syncs pins to Pinterest drip-feed queue.
    7. Updates idea status to 'published' and saves pipeline history.
    """
    selected_idea = None
    all_ideas = []
    try:
        from db import get_ideas, save_idea, update_idea_status

        all_ideas = get_ideas()
    except Exception as e:
        log.warning("Erro ao buscar ideias no banco para autopilot: %s", e)

    if idea_id is not None:
        for item in all_ideas:
            if (item.get("idea_id") == idea_id) or (item.get("id") == idea_id):
                selected_idea = item
                break
    else:
        # First priority: pending ideas matching category_filter (e.g. buyer_intent)
        if category_filter:
            for item in all_ideas:
                cat = str(item.get("category", "")).lower()
                src = str(item.get("source", "")).lower()
                status = str(item.get("status", "")).lower()
                if status == "pending" and (category_filter in cat or category_filter in src):
                    selected_idea = item
                    break
        # Second priority: any pending idea
        if not selected_idea:
            for item in all_ideas:
                if str(item.get("status", "")).lower() == "pending":
                    selected_idea = item
                    break
        # Fallback: if no pending ideas exist, generate new buyer intent ideas
        if not selected_idea:
            try:
                from dashboard.routes.ideas import _generate_buyer_intent_ideas

                generated = _generate_buyer_intent_ideas()
                if generated and isinstance(generated, list):
                    max_id = max((i.get("idea_id") or i.get("id") or 0 for i in all_ideas), default=0)
                    for idx, idea in enumerate(generated):
                        idea["idea_id"] = max_id + idx + 1
                        idea["status"] = "pending"
                        idea["created_at"] = datetime.now().isoformat()
                        idea["source"] = "buyer_intent"
                        try:
                            save_idea(idea)
                        except Exception:
                            pass
                    selected_idea = generated[0]
            except Exception as e:
                log.warning("Erro ao gerar ideias de fallback no autopilot: %s", e)

    if not selected_idea:
        return {
            "success": False,
            "error": "Nenhuma pauta pendente disponível para o Piloto Automático.",
        }

    target_id = selected_idea.get("idea_id") or selected_idea.get("id")
    keyword = (selected_idea.get("keyword") or selected_idea.get("title") or "").strip()
    if not keyword:
        return {"success": False, "error": "Ideia selecionada sem palavra-chave ou título válido."}

    # Mark as in_progress
    if target_id:
        try:
            update_idea_status(target_id, "in_progress")
        except Exception:
            pass

    log.info("Autopilot iniciando ciclo para pauta '%s' (id=%s)", keyword, target_id)
    pipeline_res = _run_pipeline_logic(
        keyword=keyword,
        skip_publish=skip_publish,
        skip_pinterest=skip_pinterest,
        force_restart=force_restart,
    )

    if pipeline_res.get("success"):
        if target_id:
            try:
                update_idea_status(target_id, "published")
            except Exception:
                pass
        return {
            "success": True,
            "autopilot": True,
            "idea": selected_idea,
            "keyword": keyword,
            "title": pipeline_res.get("title"),
            "article": pipeline_res.get("article"),
            "post_url": pipeline_res.get("post_url"),
            "bridge_url": pipeline_res.get("bridge_url"),
            "image_url": pipeline_res.get("image_url"),
            "steps": pipeline_res.get("steps", []),
        }
    else:
        # Revert status so it can be retried
        if target_id:
            try:
                update_idea_status(target_id, "pending")
            except Exception:
                pass
        return {
            "success": False,
            "autopilot": True,
            "idea": selected_idea,
            "keyword": keyword,
            "error": pipeline_res.get("error") or "Falha ao executar etapas do pipeline",
            "steps": pipeline_res.get("steps", []),
        }


