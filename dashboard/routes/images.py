# -*- coding: utf-8 -*-
"""Images API routes."""
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request

from dashboard.services.articles import _extract_article_info
from dashboard.services.helpers import (
    _articles_dir,
    _env,
    _images_dir,
    login_required,
)
from dashboard.services.images import _build_pin_prompt
from image_generator import (
    extract_slug_from_filename,
    generate_article_pins,
    generate_image,
    generate_pin_prompt_variations,
)

images_bp = Blueprint("images", __name__, url_prefix="/api/images")


@images_bp.route("/generate", methods=["POST"])
@login_required
def api_generate_image():
    """Generate image from text prompt."""
    try:
        data = request.json or {}
        prompt = data.get("prompt", "").strip()
        filename = data.get("filename", "pin.png")
        usage = data.get("usage", "square")
        if not prompt:
            return jsonify({"success": False, "error": "Prompt obrigatório"}), 400

        api_key = _env("GEMINI_API_KEY")
        image_bytes, provider = generate_image(prompt=prompt, api_key=api_key, usage=usage)

        images_dir = _images_dir()
        (images_dir / filename).write_bytes(image_bytes)

        return jsonify({
            "success": True,
            "filename": filename,
            "size_kb": round(len(image_bytes) / 1024, 1),
            "provider": provider,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@images_bp.route("/generate_pin", methods=["POST"])
@login_required
def api_generate_pin_for_article():
    """Generate vertical Pinterest pin tailored to an article."""
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

        images_dir = _images_dir()
        (images_dir / pin_filename).write_bytes(image_bytes)

        return jsonify({
            "success": True,
            "filename": pin_filename,
            "article": filename,
            "title": article_info["title"],
            "description": article_info["meta_description"],
            "slug": article_info["slug"],
            "tags": article_info["tags"],
            "excerpt": article_info["excerpt"],
            "size_kb": round(len(image_bytes) / 1024, 1),
            "url": f"/static/images/{pin_filename}",
            "prompt_used": prompt,
            "provider": provider,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@images_bp.route("/generate_pin_variations", methods=["POST"])
@login_required
def api_generate_pin_variations():
    """Generate multiple Pinterest pin variations for the same article."""
    try:
        data = request.json or {}
        filename = data.get("filename", "").strip()
        count = min(max(int(data.get("count", 3)), 2), 5)
        if not filename:
            return jsonify({"success": False, "error": "Arquivo obrigatório"}), 400

        filepath = _articles_dir() / filename
        if not filepath.exists():
            return jsonify({"success": False, "error": f"Arquivo não encontrado: {filename}"}), 404

        article_info = _extract_article_info(filepath)
        slug = extract_slug_from_filename(filename)
        api_key = _env("GEMINI_API_KEY")

        results = generate_article_pins(
            api_key=api_key,
            article_title=article_info["title"],
            article_excerpt=article_info["excerpt"],
            keywords=article_info["keywords"] + article_info["tags"],
            count=count,
        )

        images_dir = _images_dir()
        saved = []
        for i, (image_bytes, provider, prompt) in enumerate(results):
            suffix = f"-v{i+1}" if i > 0 else ""
            pin_filename = f"pin-{slug}{suffix}.png"
            (images_dir / pin_filename).write_bytes(image_bytes)
            saved.append({
                "filename": pin_filename,
                "url": f"/static/images/{pin_filename}",
                "size_kb": round(len(image_bytes) / 1024, 1),
                "provider": provider,
                "prompt_used": prompt,
                "variation": i + 1,
            })

        return jsonify({
            "success": True,
            "article": filename,
            "title": article_info["title"],
            "count": len(saved),
            "pins": saved,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@images_bp.route("/preview_prompt", methods=["POST"])
@login_required
def api_preview_prompt():
    """Preview smart prompt text without generating the image."""
    try:
        data = request.json or {}
        filename = data.get("filename", "").strip()
        usage = data.get("usage", "pinterest")
        variations = data.get("variations", False)

        if not filename:
            return jsonify({"success": False, "error": "Arquivo obrigatório"}), 400

        filepath = _articles_dir() / filename
        if not filepath.exists():
            return jsonify({"success": False, "error": f"Arquivo não encontrado: {filename}"}), 404

        article_info = _extract_article_info(filepath)
        api_key = _env("GEMINI_API_KEY")

        if variations:
            count = min(max(int(data.get("count", 3)), 2), 5)
            prompts = generate_pin_prompt_variations(
                api_key=api_key,
                article_title=article_info["title"],
                article_excerpt=article_info["excerpt"],
                keywords=article_info["keywords"] + article_info["tags"],
                count=count,
            )
            return jsonify({
                "success": True,
                "title": article_info["title"],
                "prompts": prompts,
            })
        else:
            prompt = _build_pin_prompt(article_info, usage=usage)
            return jsonify({
                "success": True,
                "title": article_info["title"],
                "prompt": prompt,
                "usage": usage,
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@images_bp.route("/list")
@login_required
def api_list_images():
    """List all generated images in static/images."""
    images_dir = _images_dir()
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


@images_bp.route("/delete/<filename>", methods=["DELETE"])
@login_required
def api_delete_image(filename):
    """Delete an image file from static/images."""
    try:
        images_dir = _images_dir()
        filepath = images_dir / filename
        if not filepath.exists():
            return jsonify({"success": False, "error": f"Imagem não encontrada: {filename}"}), 404
        filepath.unlink()
        return jsonify({"success": True, "filename": filename})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@images_bp.route("/pin_info/<filename>")
@login_required
def api_pin_info(filename: str):
    """Retrieve article info associated with a pin filename."""
    slug = filename.replace("pin-", "").replace(".png", "")
    for f in _articles_dir().glob("*.md"):
        if extract_slug_from_filename(f.name) == slug:
            info = _extract_article_info(f)
            site_url = _env("SITE_URL", "https://tech-tips.ct.ws")
            return jsonify({
                "success": True,
                "title": info["title"],
                "description": info["meta_description"],
                "excerpt": info["excerpt"],
                "tags": info["tags"],
                "link": f"{site_url.rstrip('/')}/?p={info['slug']}",
                "article_file": f.name,
            })
    return jsonify({"success": False, "error": "Artigo não encontrado"}), 404
