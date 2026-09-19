# -*- coding: utf-8 -*-
"""Articles and verification API routes."""
import json
import re
from datetime import datetime

from flask import Blueprint, jsonify, request

from dashboard.services.articles import _extract_article_info
from dashboard.services.gemini import _gemini_call
from dashboard.services.helpers import (
    _articles_dir,
    _env,
    _parse_json,
    login_required,
)
from db import get_verify_history, save_verify_history

articles_bp = Blueprint("articles", __name__, url_prefix="/api")


@articles_bp.route("/generate", methods=["POST"])
@login_required
def api_generate_article():
    """Generate a complete Markdown article from a keyword using Gemini AI."""
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


@articles_bp.route("/articles/list")
@login_required
def api_list_articles():
    """List all saved markdown articles."""
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


@articles_bp.route("/articles/delete/<filename>", methods=["DELETE"])
@login_required
def api_delete_article(filename):
    """Delete a markdown article from disk."""
    try:
        if not filename.endswith(".md"):
            return jsonify({"success": False, "error": "Apenas arquivos .md podem ser removidos"}), 400
        filepath = _articles_dir() / filename
        if not filepath.exists():
            return jsonify({"success": False, "error": f"Arquivo não encontrado: {filename}"}), 404
        filepath.unlink()
        return jsonify({"success": True, "filename": filename})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@articles_bp.route("/verify", methods=["POST"])
@login_required
def api_verify_article():
    """Evaluate article for SEO quality with optional Gemini review."""
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

        images = body.lower().count("<img") + len(re.findall(r'!\[.*?\]\(.*?\)', body))
        if images == 0:
            warnings.append("Sem imagens no artigo")

        if "meta_description" not in content[:500]:
            warnings.append("Sem meta description")

        score = max(0, score)
        status = "Aprovado" if score >= 70 else "Reprovado"

        # Gemini AI review (optional)
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

        history = get_verify_history()
        history.append(result)
        history = history[-50:]
        save_verify_history(history[-1] if history else {})

        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@articles_bp.route("/verify/history/delete/<int:index>", methods=["DELETE"])
@login_required
def api_delete_verify_history(index):
    """Delete a verification history entry by index."""
    try:
        history = get_verify_history()
        if index < 0 or index >= len(history):
            return jsonify({"success": False, "error": f"Índice inválido: {index}"}), 404
        removed = history.pop(index)
        save_verify_history(history[-1] if history else {})
        return jsonify({"success": True, "deleted": removed})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
