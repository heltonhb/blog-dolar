#!/usr/bin/env python3
"""
Blog em Dolar - Image Generator Module
Generates images for blog articles using free AI providers.

Providers (in order of preference):
1. Gemini Imagen (via Google Gemini API - free tier)
2. Pollinations.ai (free, unlimited, lower quality - fallback)

Features:
- Smart prompt generation using Gemini text model
- Multiple aspect ratios (Pinterest pin, featured image, inline)
- Multi-provider fallback
- Featured image upload to WordPress
"""

import base64
import hashlib
import io
import os
import random
import re
import time
from pathlib import Path
from typing import Optional

try:
    import httpx
except ImportError:
    os.system(f"pip install httpx -q")
    import httpx

try:
    from image_cache import env_value, get_cached, image_cache_key, put_cached
except ImportError:  # imported as scripts.image_generator
    from scripts.image_cache import env_value, get_cached, image_cache_key, put_cached


# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

ASPECT_RATIOS = {
    "pinterest": "2:3",     # Vertical pin (ideal for Pinterest)
    "featured": "16:9",     # Wide banner for WordPress featured image
    "inline": "16:9",       # Wide image for article body
    "square": "1:1",        # Square fallback
}

# Dimensions for Pollinations fallback (which uses width/height, not aspect ratio)
DIMENSIONS = {
    "pinterest": (768, 1152),
    "featured": (1200, 675),
    "inline": (800, 450),
    "square": (1024, 1024),
}


# ---------------------------------------------------------------------------
#  Smart Prompt Generation (uses Gemini text model)
# ---------------------------------------------------------------------------

def generate_smart_prompt(
    api_key: str,
    article_title: str,
    article_excerpt: str = "",
    keywords: list[str] = None,
    target: str = "pinterest pin",
    model: str = "gemini-3.1-flash-lite",
) -> str:
    """Use Gemini text model to create an optimal image generation prompt.

    This is the core "Google Flow" prompt generator — it deeply analyzes the
    article content and produces a highly specific, visually rich prompt that
    the image generator (Gemini Imagen / FLUX / Pollinations) can turn into
    an image that is immediately recognizable as related to the article topic.

    The prompt engineering follows Pinterest best practices:
    - Hero object / scene that tells the story at a glance
    - Specific color palette and lighting directives
    - Composition rules (rule of thirds, negative space for overlay)
    - Style consistency (editorial photography or flat illustration)

    Args:
        api_key: Gemini API key
        article_title: Title of the article
        article_excerpt: First ~500 chars of the article body
        keywords: Extracted keywords from headings
        target: Type of image (e.g., 'pinterest pin', 'blog featured image')
        model: Gemini text model to use

    Returns:
        A detailed, optimized image generation prompt
    """
    if not api_key:
        return _build_fallback_prompt(article_title, keywords or [])

    kw_str = ", ".join(keywords[:8]) if keywords else ""
    excerpt_part = f"\nArticle excerpt: {article_excerpt[:600]}" if article_excerpt else ""

    import datetime
    month = datetime.datetime.now().month
    quarter = f"Q{(month - 1) // 3 + 1}"
    seasonal_hints = {
        "Q1": "fresh start energy, clean whites and blues, organized minimalist aesthetic, crisp winter light",
        "Q2": "warm golden light, lush greens, dynamic outdoor-inspired freshness, spring/summer vibrancy",
        "Q3": "vibrant saturated colors, bold contrasts, sun-drenched glamour, peak summer energy",
        "Q4": "warm amber lighting, cozy atmosphere, premium holiday feel, rich deep tones with gold accents",
    }
    seasonal_hint = seasonal_hints.get(quarter, "modern professional aesthetic")

    # Determine if the topic is more "product/hardware" or "concept/software"
    product_keywords = {"laptop", "pc", "monitor", "headphone", "keyboard", "mouse",
                        "ssd", "nvme", "router", "phone", "tablet", "camera", "gpu",
                        "cpu", "ram", "cable", "charger", "speaker", "drone", "watch"}
    concept_keywords = {"vpn", "privacy", "security", "speed", "wifi", "cloud",
                        "ai", "machine learning", "programming", "code", "hack",
                        "tips", "guide", "tutorial", "review", "comparison", "budget",
                        "travel", "remote", "freelance", "productivity"}

    title_lower = article_title.lower()
    is_product = any(kw in title_lower for kw in product_keywords)
    is_concept = any(kw in title_lower for kw in concept_keywords)

    if is_product:
        style_directive = (
            "Use a PRODUCT PHOTOGRAPHY style: the main product/device as hero subject "
            "on a clean surface, shallow depth of field, studio lighting with soft shadows, "
            "lifestyle context (desk, workspace, hands using it). Think Apple product photography."
        )
    elif is_concept:
        style_directive = (
            "Use a CONCEPTUAL ILLUSTRATION style: create a visual metaphor that represents "
            "the abstract concept. Use symbolic elements, creative compositions, maybe "
            "isometric 3D render or editorial infographic aesthetic. Think Dribbble/Behance quality."
        )
    else:
        style_directive = (
            "Use an EDITORIAL PHOTOGRAPHY style: a striking, magazine-quality scene that "
            "tells the story of the article at a glance. Rich details, professional composition, "
            "cinematic lighting."
        )

    prompt = f"""You are a world-class visual director creating image prompts for AI image generation.
Your job: analyze this article and produce ONE highly specific, visually rich image prompt
that will generate a stunning {target}.

{style_directive}

Seasonal mood: {seasonal_hint}

═══ ARTICLE TO ANALYZE ═══
Title: {article_title}{excerpt_part}
Keywords: {kw_str}
═══════════════════════════

Follow this mental process (but output ONLY the final prompt):
1. IDENTIFY the single most iconic visual element of this topic
   (What object/scene would someone INSTANTLY associate with this subject?)
2. COMPOSE the scene: place the hero element using rule of thirds
3. SPECIFY exact lighting: direction, warmth, shadows, highlights
4. DEFINE color palette: 2-3 dominant colors + 1 accent
5. ADD environmental context: background, surface, atmosphere
6. INCLUDE fine details that make it feel real and premium

STRICT RULES for your output prompt:
- Be HYPER-SPECIFIC: say "matte black mechanical keyboard with cherry MX switches
  and warm RGB backlighting" NOT "a keyboard"
- NEVER include any text, words, letters, logos, watermarks, or UI elements
- Specify the camera angle (top-down, 45°, eye-level, macro close-up)
- Mention depth of field (shallow bokeh, deep focus, tilt-shift)
- The image must be INSTANTLY recognizable as related to "{article_title}"
- Leave the lower 30% of the composition slightly darker/simpler for text overlay space
- Output 60-120 words maximum

Return ONLY the image generation prompt. No quotes, no labels, no explanation."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 300},
    }

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            clean = result.strip().strip('"').strip("'").strip()
            # Remove any prefix labels the model might add
            for prefix in ["Image prompt:", "Prompt:", "Here is", "Here's"]:
                if clean.lower().startswith(prefix.lower()):
                    clean = clean[len(prefix):].strip().strip(":").strip()
            return clean
    except Exception as e:
        print(f"  ⚠️ Smart prompt generation failed ({e}), using fallback")
        return _build_fallback_prompt(article_title, keywords or [])


def generate_pin_prompt_variations(
    api_key: str,
    article_title: str,
    article_excerpt: str = "",
    keywords: list[str] = None,
    count: int = 3,
    model: str = "gemini-2.0-flash",
) -> list[str]:
    """Generate multiple distinct visual angle prompts for the same article.

    Pinterest rewards variety — posting 3-5 different pins for the same article
    with different visual approaches increases reach significantly.

    Args:
        api_key: Gemini API key
        article_title: Title of the article
        article_excerpt: First ~500 chars of the article body
        keywords: Extracted keywords from headings
        count: Number of variations (2-5)
        model: Gemini text model to use

    Returns:
        List of distinct image generation prompts
    """
    if not api_key:
        base = _build_fallback_prompt(article_title, keywords or [])
        return [base]

    count = max(2, min(count, 5))
    kw_str = ", ".join(keywords[:6]) if keywords else ""
    excerpt_part = f"\nExcerpt: {article_excerpt[:400]}" if article_excerpt else ""

    prompt = f"""You are a Pinterest content strategist and visual director.
Generate {count} COMPLETELY DIFFERENT image prompts for the same blog article.
Each prompt must show the topic from a unique visual angle.

Article: {article_title}{excerpt_part}
Keywords: {kw_str}

For each variation, use a DIFFERENT visual approach:
1. HERO PRODUCT SHOT — Close-up, studio lighting, the main subject as star
2. LIFESTYLE SCENE — The subject in real-world use, environmental context
3. FLAT LAY / TOP-DOWN — Organized arrangement of related items from above
4. CONCEPTUAL / ABSTRACT — Visual metaphor, artistic interpretation
5. INFOGRAPHIC STYLE — Clean illustration with visual hierarchy (but NO text)

Rules for EACH prompt:
- 60-100 words, hyper-specific visual details
- NO text, words, letters, logos, or watermarks in the image
- Specify lighting, colors, camera angle, depth of field
- Must be INSTANTLY recognizable as related to the article topic
- Reserve lower 30% for text overlay (keep it simpler/darker there)

Return ONLY a JSON array of strings, each string being one prompt.
Example: ["prompt 1 here", "prompt 2 here", "prompt 3 here"]"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 800},
    }

    try:
        with httpx.Client(timeout=45) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]

        # Parse JSON array from response
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
        raw = raw.strip()

        import json as _json
        match = re.search(r'\[[\s\S]*\]', raw)
        if match:
            prompts = _json.loads(match.group())
            if isinstance(prompts, list) and len(prompts) >= 2:
                return [str(p).strip() for p in prompts[:count]]

        # Fallback: split by numbered lines
        lines = [l.strip().strip('"').strip("'") for l in raw.split("\n") if len(l.strip()) > 30]
        if len(lines) >= 2:
            return lines[:count]

    except Exception as e:
        print(f"  ⚠️ Pin variations failed ({e}), using single prompt")

    # Final fallback: generate one smart prompt
    return [generate_smart_prompt(api_key, article_title, article_excerpt, keywords)]


def _build_fallback_prompt(title: str, keywords: list[str]) -> str:
    """Fallback prompt builder when Gemini text API is unavailable."""
    # Extract meaningful words from title
    stop_words = {"the", "a", "an", "is", "are", "how", "to", "for", "and", "or",
                  "in", "on", "at", "of", "your", "you", "with", "this", "that",
                  "best", "top", "guide", "ultimate", "complete", "vs"}
    title_words = [w.lower() for w in title.split() if w.lower() not in stop_words and len(w) > 2]
    visual_terms = title_words[:4]

    if keywords:
        clean_kw = []
        for kw in keywords[:3]:
            cleaned = re.sub(r'^[\d\.\)]+\s*', '', kw).strip()
            cleaned = re.sub(r'^(Phase|Step|Chapter)\s+\d+[:\.]?\s*', '', cleaned, flags=re.IGNORECASE).strip()
            words = cleaned.split()
            if 1 <= len(words) <= 4 and len(cleaned) < 35:
                clean_kw.append(cleaned.lower())
        if clean_kw:
            visual_terms = clean_kw

    subject = ", ".join(visual_terms) if visual_terms else title[:50]
    return (
        f"Professional editorial photography of {subject}. "
        f"Shot at 45-degree angle with shallow depth of field, "
        f"soft directional lighting from the left, warm color temperature. "
        f"Clean modern desk surface, subtle bokeh background. "
        f"Rich details, premium quality, magazine-worthy composition. "
        f"No text, no words, no watermarks."
    )


# ---------------------------------------------------------------------------
#  Image Generation: Gemini Imagen
# ---------------------------------------------------------------------------

def generate_image_gemini(
    api_key: str,
    prompt: str,
    aspect_ratio: str = "3:4",
    model: str = "gemini-2.5-flash-image",
) -> bytes:
    """Generate an image using Google Gemini API.

    Args:
        api_key: Gemini API key
        prompt: Image generation prompt
        aspect_ratio: One of '1:1', '3:4', '4:3', '9:16', '16:9'
        model: Gemini model to use

    Returns:
        Raw image bytes (PNG)

    Raises:
        RuntimeError: If image generation fails after retries
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": [{"text": f"Generate an image: {prompt}"}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }

    last_err = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=90) as client:
                resp = client.post(url, json=payload)

                if resp.status_code in (429, 503):
                    wait = 5 * (attempt + 1)
                    print(f"  ⏳ Gemini rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    last_err = f"HTTP {resp.status_code}"
                    continue

                resp.raise_for_status()
                data = resp.json()

            candidates = data.get("candidates", [])
            for candidate in candidates:
                parts = candidate.get("content", {}).get("parts", [])
                for part in parts:
                    if "inlineData" in part:
                        import base64 as _b64
                        return _b64.b64decode(part["inlineData"]["data"])

            raise ValueError("Gemini returned no image data")

        except Exception as e:
            last_err = str(e)
            if attempt < 2:
                print(f"  ⚠️ Gemini attempt {attempt+1} failed: {e}")
                time.sleep(2)
            continue

    raise RuntimeError(f"Gemini failed after 3 attempts: {last_err}")


# ---------------------------------------------------------------------------
#  Image Generation: Pollinations.ai (fallback)
# ---------------------------------------------------------------------------

def generate_image_pollinations(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    seed: int = None,
    **kwargs,
) -> bytes:
    """Generate an image using Pollinations.ai (free, no API key required).

    Args:
        prompt: Image generation prompt
        width: Image width in pixels
        height: Image height in pixels
        seed: Random seed for reproducibility

    Returns:
        Raw image bytes (PNG/JPEG)
    """
    import urllib.parse

    if seed is None:
        seed = random.randint(1, 999999)

    # Enhance prompt for better quality
    enhanced = f"professional, high quality, detailed, sharp focus, 4k, {prompt}"
    encoded_prompt = urllib.parse.quote(enhanced)
    url_turbo = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={seed}&model=turbo"
    url_base = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={seed}"
    url_flux = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={seed}&model=flux"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    with httpx.Client(headers=headers, timeout=120, follow_redirects=True) as client:
        for attempt in range(3):
            for candidate_url in (url_turbo, url_base, url_flux):
                try:
                    resp = client.get(candidate_url)
                    if resp.status_code == 200 and len(resp.content) >= 5000:
                        return resp.content
                except Exception:
                    continue
            if attempt < 2:
                time.sleep(3)

    raise ValueError(f"Pollinations returned invalid or too-small image")


def generate_image_together(
    prompt: str,
    api_key: str = "",
    width: int = 1024,
    height: int = 1024,
    **kwargs,
) -> bytes:
    """Generate an image using Together AI FLUX model (high quality).

    Args:
        prompt: Image generation prompt
        api_key: Together AI API key
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Raw image bytes (PNG)
    """
    import base64 as _b64

    url = "https://api.together.xyz/v1/images/generations"
    payload = {
        "model": "black-forest-labs/FLUX.1-schnell-Free",
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": 4,
        "n": 1,
        "response_format": "b64_json",
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = httpx.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()

    data = resp.json()
    images = data.get("data", [])
    if images and "b64_json" in images[0]:
        return _b64.b64decode(images[0]["b64_json"])

    raise ValueError("Together AI returned no image data")


# ---------------------------------------------------------------------------
#  Multi-provider Fallback
# ---------------------------------------------------------------------------

def generate_image_huggingface(
    prompt: str,
    api_key: str = "",
    width: int = 1024,
    height: int = 1024,
    **kwargs,
) -> bytes:
    """Generate an image via Hugging Face Inference Providers (needs HF_TOKEN).

    Anonymous access is rejected (401), so this provider is only part of the
    chain when ``IMAGE_PROVIDER=huggingface`` **and** a token is configured.
    """
    model = env_value("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
    url = f"https://router.huggingface.co/hf-inference/models/{model}"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    payload = {"inputs": prompt, "parameters": {"width": width, "height": height}}

    resp = httpx.post(url, json=payload, headers=headers, timeout=120)
    if resp.status_code in (401, 403):
        raise RuntimeError("Hugging Face: HF_TOKEN ausente ou inválido")
    resp.raise_for_status()

    content_type = resp.headers.get("content-type", "")
    if "image" in content_type:
        data = resp.content
    else:
        # Providers sometimes answer JSON (error object or base64 payload)
        try:
            body = resp.json()
        except Exception:
            data = resp.content
        else:
            if isinstance(body, dict) and body.get("error"):
                raise RuntimeError(f"Hugging Face: {body['error']}")
            if isinstance(body, dict) and body.get("image"):
                import base64 as _b64
                data = _b64.b64decode(body["image"])
            else:
                data = resp.content

    if len(data) < 5000:
        raise ValueError(f"Hugging Face returned too-small image ({len(data)} bytes)")
    return data


# ---------------------------------------------------------------------------
#  Multi-provider fallback (IMAGE_PROVIDER + prompt cache)
# ---------------------------------------------------------------------------

# Providers tried (in order) when IMAGE_PROVIDER is unset or "auto".
AUTO_ORDER = ("together-flux", "gemini-imagen", "pollinations")

# Accepted IMAGE_PROVIDER spellings -> canonical provider name.
PROVIDER_ALIASES = {
    "auto": "auto",
    "together": "together-flux",
    "together-flux": "together-flux",
    "gemini": "gemini-imagen",
    "imagen": "gemini-imagen",
    "gemini-imagen": "gemini-imagen",
    "huggingface": "huggingface",
    "hf": "huggingface",
    "pollinations": "pollinations",
}


def _normalize_provider(value: str) -> str:
    """Map a raw IMAGE_PROVIDER value to a canonical name ('auto' if unknown)."""
    return PROVIDER_ALIASES.get((value or "auto").strip().lower(), "auto")


def _provider_chain(preferred: str, available: list[str]) -> list[str]:
    """Order the providers to try.

    ``preferred`` (from IMAGE_PROVIDER) goes first; the remaining providers
    follow in auto order so a failure never kills the generation. An
    unavailable/unknown preference silently degrades to the auto order.
    """
    preferred = _normalize_provider(preferred)
    auto = [p for p in AUTO_ORDER if p in available]
    if preferred == "auto" or preferred not in available:
        return auto
    return [preferred] + [p for p in auto if p != preferred]


def _provider_callers(api_key: str, usage: str) -> dict:
    """Map of provider name -> zero-arg callable for the given usage."""
    callers = {}

    together_key = env_value("TOGETHER_API_KEY", "")
    if together_key:
        w, h = DIMENSIONS.get(usage, (1024, 1024))
        callers["together-flux"] = lambda p: generate_image_together(
            p, api_key=together_key, width=w, height=h
        )

    if api_key:
        aspect = ASPECT_RATIOS.get(usage, "1:1")
        callers["gemini-imagen"] = lambda p: generate_image_gemini(
            api_key, p, aspect_ratio=aspect
        )

    hf_token = env_value("HF_TOKEN", "") or env_value("HUGGINGFACE_API_TOKEN", "")
    if hf_token:
        w, h = DIMENSIONS.get(usage, (1024, 1024))
        callers["huggingface"] = lambda p: generate_image_huggingface(
            p, api_key=hf_token, width=w, height=h
        )

    # Pollinations (fallback - no API key needed)
    w, h = DIMENSIONS.get(usage, (1024, 1024))
    callers["pollinations"] = lambda p: generate_image_pollinations(
        p, width=w, height=h
    )
    return callers


def generate_image(
    prompt: str,
    api_key: str = "",
    usage: str = "pinterest",
    **kwargs,
) -> tuple[bytes, str]:
    """Generate an image using the best available provider.

    Order comes from IMAGE_PROVIDER (``auto`` | ``gemini`` | ``pollinations`` |
    ``together`` | ``huggingface``), with automatic fallback to the rest of the
    chain. Results are cached in ``cache/images/`` keyed by the hash of the
    prompt + usage + provider (TTL: IMAGE_CACHE_TTL_DAYS, default 7 days), so
    retries and repeated pipeline runs cost no API calls.

    Args:
        prompt: Image generation prompt
        api_key: Gemini API key (required for Gemini, optional for the others)
        usage: Target usage - 'pinterest', 'featured', 'inline', or 'square'

    Returns:
        Tuple of (image_bytes, provider_name)
    """
    callers = _provider_callers(api_key, usage)
    raw_preferred = env_value("IMAGE_PROVIDER", "auto")
    if _normalize_provider(raw_preferred) == "auto" and (
        raw_preferred or "auto"
    ).strip().lower() not in ("", "auto"):
        print(f"  ⚠️ IMAGE_PROVIDER desconhecido: {raw_preferred!r} — usando 'auto'")

    chain = _provider_chain(raw_preferred, list(callers))
    if not chain:
        raise RuntimeError("Nenhum provider de imagem disponível (sem chaves de API).")

    # 1) Cache: any provider in the chain with a fresh entry wins (no API call)
    for name in chain:
        cached = get_cached(image_cache_key(prompt, usage, name))
        if cached and len(cached) > 5000:
            print(f"  📦 Imagem servida do cache ({name}, {len(cached) // 1024}KB)")
            return cached, name

    # 2) Generate through the chain, caching the first success
    last_err = None
    for name in chain:
        try:
            print(f"  🎨 Tentando {name}...")
            image_bytes = callers[name](prompt)
            if len(image_bytes) > 5000:
                put_cached(
                    image_cache_key(prompt, usage, name),
                    image_bytes,
                    meta={"provider": name, "usage": usage, "prompt": prompt[:200]},
                )
                print(f"  ✅ Imagem gerada via {name} ({len(image_bytes) // 1024}KB)")
                return image_bytes, name
            last_err = f"{name} retornou imagem muito pequena"
        except Exception as e:
            last_err = str(e)
            print(f"  ⚠️ {name} falhou: {e}")
            continue

    raise RuntimeError(f"Todos os providers falharam. Último erro: {last_err}")


# ---------------------------------------------------------------------------
#  High-level: Generate image for article
# ---------------------------------------------------------------------------

def generate_article_image(
    api_key: str,
    article_title: str,
    article_excerpt: str = "",
    keywords: list[str] = None,
    usage: str = "pinterest",
    custom_prompt: str = "",
) -> tuple[bytes, str, str]:
    """Full pipeline: generate smart prompt → generate image.

    Uses the "Google Flow" approach: Gemini analyzes the article content
    and generates a hyper-specific image prompt, which is then sent to
    the best available image generation provider.

    Args:
        api_key: Gemini API key
        article_title: Article title
        article_excerpt: First ~500 chars of article body (HTML stripped)
        keywords: Keywords extracted from headings
        usage: 'pinterest', 'featured', 'inline', or 'square'
        custom_prompt: Override the auto-generated prompt

    Returns:
        Tuple of (image_bytes, provider_name, prompt_used)
    """
    target_map = {
        "pinterest": "Pinterest pin (vertical 3:4 ratio, bold eye-catching hero image for social media feed)",
        "featured": "blog featured hero banner (wide 16:9, professional editorial photography quality)",
        "inline": "blog section illustration (wide 16:9, informative, contextual to the heading topic)",
        "square": "social media square thumbnail (1:1, clean, bold focal point)",
    }

    # Generate smart prompt if not provided
    if custom_prompt:
        prompt = custom_prompt
    else:
        target = target_map.get(usage, "blog illustration")
        prompt = generate_smart_prompt(
            api_key=api_key,
            article_title=article_title,
            article_excerpt=article_excerpt,
            keywords=keywords,
            target=target,
        )

    print(f"  🧠 Prompt gerado: {prompt[:120]}...")

    # Generate the image
    image_bytes, provider = generate_image(
        prompt=prompt,
        api_key=api_key,
        usage=usage,
    )

    # Apply Pinterest text overlay to the generated pin image
    if usage == "pinterest":
        headline = _pin_headline(article_title)
        if headline:
            try:
                image_bytes = add_pin_text_overlay(image_bytes, headline)
                print(f"  📝 Overlay aplicado no pin: {headline}")
            except Exception as e:
                print(f"  ⚠️ Overlay de texto pulado ({e})")

    return image_bytes, provider, prompt


def generate_article_pins(
    api_key: str,
    article_title: str,
    article_excerpt: str = "",
    keywords: list[str] = None,
    count: int = 3,
) -> list[tuple[bytes, str, str]]:
    """Generate multiple Pinterest pin variations for the same article.

    Pinterest algorithm rewards fresh content variety — posting 3-5 different
    pins for the same article with different visual angles significantly
    increases total reach and click-through rate.

    Uses generate_pin_prompt_variations() to get distinct visual approaches,
    then generates an image for each.

    Args:
        api_key: Gemini API key
        article_title: Article title
        article_excerpt: First ~500 chars of article body
        keywords: Keywords extracted from headings
        count: Number of pin variations to generate (2-5)

    Returns:
        List of (image_bytes, provider_name, prompt_used) tuples
    """
    prompts = generate_pin_prompt_variations(
        api_key=api_key,
        article_title=article_title,
        article_excerpt=article_excerpt,
        keywords=keywords,
        count=count,
    )

    results = []
    headline = _pin_headline(article_title)

    for i, prompt in enumerate(prompts, 1):
        print(f"\n  🎨 Variação {i}/{len(prompts)}")
        print(f"  🧠 Prompt: {prompt[:100]}...")

        try:
            image_bytes, provider = generate_image(
                prompt=prompt,
                api_key=api_key,
                usage="pinterest",
            )

            # Apply text overlay
            if headline:
                try:
                    image_bytes = add_pin_text_overlay(image_bytes, headline)
                except Exception:
                    pass

            results.append((image_bytes, provider, prompt))
            print(f"  ✅ Variação {i} gerada ({len(image_bytes) // 1024}KB via {provider})")

        except Exception as e:
            print(f"  ⚠️ Variação {i} falhou: {e}")
            continue

        # Small delay between generations to avoid rate limiting
        if i < len(prompts):
            time.sleep(2)

    if not results:
        # Emergency fallback: try a single generation
        print("  ⚠️ Todas as variações falharam, tentando geração padrão...")
        img, prov, prompt = generate_article_image(
            api_key=api_key,
            article_title=article_title,
            article_excerpt=article_excerpt,
            keywords=keywords,
            usage="pinterest",
        )
        results.append((img, prov, prompt))

    return results


# ---------------------------------------------------------------------------
#  Pinterest: text overlay + pin title/description/hashtags
#  (texto sobre a imagem é a recomendação nº 1 do Pinterest para CTR/alcance)
# ---------------------------------------------------------------------------

import logging as _logging

_logger = _logging.getLogger(__name__)

# Fontes preferidas (Debian/Ubuntu de fábrica). Se nenhuma existir, usamos
# a fonte bitmap do Pillow como fallback (menor, mas funciona em qualquer lugar).
_BOLD_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
]


def _find_bold_font() -> Optional[str]:
    for path in _BOLD_FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def _pin_headline(title: str, max_words: int = 5) -> str:
    """Gera uma headline curta e impactante a partir do título do artigo.

    Pinterest quer texto curto sobre a imagem (uma frase de até ~5 palavras).
    Prioriza a keyword; descarta stopwords e filler.
    """
    if not title:
        return ""
    stop = {
        "the", "a", "an", "is", "are", "to", "for", "and", "or", "in", "on",
        "at", "of", "how", "what", "why", "your", "you", "with", "this", "that",
        "best", "top", "guide", "ultimate", "complete", "ultimate", "vs", "2026",
        "2025", "2024", "explained", "need", "know",
    }
    # Remover pontuação e normalizar minúsculas
    words = [w.strip(",:;!?()") for w in title.split()]
    meaningful = [w for w in words if w.lower() not in stop and len(w) > 2]
    chosen = meaningful or words
    headline = " ".join(chosen[:max_words])
    return headline.upper() if headline else ""


def add_pin_text_overlay(image_bytes: bytes, headline: str) -> bytes:
    """Sobrepoe `headline` no pin (fair use de texto), usando templates variados na BASE."""
    if not headline:
        return image_bytes

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise RuntimeError("Pillow nao instalado (pip install pillow)")
    
    import random

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    W, H = img.size
    
    font_path = _find_bold_font()
    target_size = max(32, int(W * 0.08))  # Tamanho maior
    if font_path:
        font = ImageFont.truetype(font_path, target_size)
        cta_font = ImageFont.truetype(font_path, max(16, int(W * 0.035)))
    else:
        font = ImageFont.load_default()
        cta_font = ImageFont.load_default()

    # Quebra em linhas
    max_width = int(W * 0.85)
    draw_temp = ImageDraw.Draw(img)
    lines = []
    for word in headline.split():
        if not lines:
            lines.append(word)
            continue
        test = lines[-1] + " " + word
        wpx = draw_temp.textlength(test, font=font)
        if wpx <= max_width or len(lines) >= 4:
            lines[-1] = test
        else:
            if len(lines) < 4:
                lines.append(word)
            break
    
    line_h = target_size + int(target_size * 0.2) if font_path else 14
    total_text_h = line_h * len(lines)
    
    # Templates variados (Ação 5)
    template = random.choice(["gradient", "solid", "split"])
    
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    
    if template == "gradient":
        # Gradiente na base (Ação 2)
        band_h = int(H * 0.45)
        start_y = H - band_h
        steps = 48
        for i in range(steps):
            y0 = start_y + int(i * band_h / steps)
            y1 = start_y + int((i + 1) * band_h / steps)
            alpha = int(240 * (i / steps))
            od.rectangle([0, y0, W, y1], fill=(0, 0, 0, alpha))
        text_y_start = H - band_h + int(band_h * 0.3)
    
    elif template == "solid":
        # Barra solida na base com borda
        band_h = total_text_h + int(H * 0.18)
        start_y = H - band_h
        od.rectangle([0, start_y, W, H], fill=(15, 15, 20, 245))
        od.line([0, start_y, W, start_y], fill=(255, 64, 129, 255), width=8)
        text_y_start = start_y + int(band_h * 0.15)
    
    else: # split
        # Split design (imagem cima, cor baixo)
        band_h = total_text_h + int(H * 0.18)
        start_y = H - band_h
        od.rectangle([0, start_y, W, H], fill=(230, 230, 235, 255))
        text_y_start = start_y + int(band_h * 0.15)

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    # Desenhar texto
    text_color = (0, 0, 0) if template == "split" else (255, 255, 255)
    shadow_color = (255, 255, 255, 180) if template == "split" else (0, 0, 0, 180)

    for i, line in enumerate(lines):
        wpx = draw.textlength(line, font=font)
        x = (W - wpx) / 2
        y = text_y_start + i * line_h
        # Shadow/Stroke 4.5:1 ratio simulado
        draw.text((x + 2, y + 2), line, font=font, fill=shadow_color)
        draw.text((x, y), line, font=font, fill=text_color)
    
    # Adicionar CTA e Branding na base (Ação 2)
    cta_text = "Read the full guide  |  Tech Tips"
    cta_w = draw.textlength(cta_text, font=cta_font)
    cta_y = H - int(H * 0.04)
    cta_color = (80, 80, 80) if template == "split" else (200, 200, 200)
    draw.text(((W - cta_w)/2, cta_y), cta_text, font=cta_font, fill=cta_color)

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


def _gemini_available(api_key: str) -> bool:
    return bool(api_key)


def generate_pin_title(api_key: str, article_title: str, excerpt: str = "") -> str:
    """Gera um titulo otimizado para pin (keyword na frente, 60-80 chars, gancho).

    Fallback: headline curta derivada do titulo do artigo.
    """
    if not article_title:
        return ""
    if not api_key:
        return _pin_headline(article_title) or article_title

    text = f"""You are a Pinterest creator expert.
Rewrite this blog article title into a high-performing Pinterest pin title.

Rules:
- Put the main keyword at the beginning.
- Maximum 80 characters, minimum 20.
- Strong hook / curiosity, but NO clickbait, NO all-caps, NO emojis.
- It must stay on-topic and be immediately clear.

Article title: {article_title}
Excerpt: {excerpt[:300]}

Return ONLY the pin title text. No quotes, no explanation."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json={
                "contents": [{"parts": [{"text": text}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 120},
            })
            resp.raise_for_status()
            result = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return result.strip().strip('"').strip("'")[:100]
    except Exception as e:
        _logger.warning("generate_pin_title fallback (%s)", e)
        return _pin_headline(article_title) or article_title


def make_hashtags(keywords, tags=None, base=None, limit: int = 5) -> list:
    """Deriva hashtags relevantes do artigo (e combina com hashtags base).

    Recomendacao: 3-5 hashtags por pin, misturando a keyword do artigo com
    hashtags genericas do nicho.
    """
    base = [b for b in (base or []) if b]
    pool: list = []

    def _add(words):
        if not words:
            return
        for w in words:
            if not w:
                continue
            s = str(w).strip().lstrip("#").strip()
            s = re.sub(r"[^a-zA-Z0-9]", "", s)
            if s:
                pool.append(s)

    _add(tags)
    _add(keywords)

    # keyword composta que ja existe (ex: "wifi" de "#wifi7")
    seen = set()
    result = []
    for s in pool:
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append("#" + s)
    result = result[:limit]

    # completa com hashtags base (nicho) que ainda nao estejam presentes
    for b in base:
        if len(result) >= limit:
            break
        bclean = b.lstrip("#")
        if bclean.lower() not in seen:
            seen.add(bclean.lower())
            result.append("#" + bclean)

    return result if result else ["#tech", "#tutorial"]


def build_pin_description(api_key: str, article_title: str, excerpt: str = "",
                          keywords=None, tags=None, base_hashtags=None) -> str:
    """Monta a descricao do pin: keyword + valor + CTA + hashtags (max ~490)."""
    if excerpt and not api_key:
        # Fallback sem Gemini: 1a frase do excerpt + CTA + hashtags
        clean = re.sub(r"\s+", " ", excerpt).strip()
        first = clean.split(". ")[0][:280]
        desc = f"{first}. Saiba mais no link."
    else:
        text = f"""You are a Pinterest creator expert.
Write a Pinterest pin DESCRIPTION (max 200 characters counts, we keep under 450 chars) for:

Title: {article_title}
Excerpt: {excerpt[:300]}

Requirements:
- Open with the main keyword naturally.
- 1-2 sentences that convey value/what the reader learns.
- End with a soft call-to-action ("Save for later" / "Read the full guide").
- NO hashtags inside the text body (they are appended separately).
Return ONLY the description text."""

        desc = article_title
        if api_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            try:
                with httpx.Client(timeout=30) as client:
                    resp = client.post(url, json={
                        "contents": [{"parts": [{"text": text}]}],
                        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 180},
                    })
                    resp.raise_for_status()
                    desc = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"')
            except Exception as e:
                _logger.warning("build_pin_description fallback (%s)", e)
                if excerpt:
                    clean = re.sub(r"\s+", " ", excerpt).strip()
                    desc = clean.split(". ")[0][:280] + ". Full guide in the link."

    hashtags = make_hashtags(keywords, tags, base_hashtags)
    desc = f"{desc} {'. '.join(hashtags)}" if hashtags else desc
    return desc[:500]


# ---------------------------------------------------------------------------
#  Inject inline images into article HTML
# ---------------------------------------------------------------------------

def inject_inline_images(
    article_html: str,
    article_slug: str,
    api_key: str,
    output_dir: Path,
    max_images: int = 2,
    site_url: str = "",
) -> tuple[str, list[str]]:
    """Insert AI-generated images into the article body after every 2nd H2.

    Args:
        article_html: Raw HTML body of the article
        article_slug: URL slug for the article (used in filenames)
        api_key: Gemini API key
        output_dir: Directory to save generated images
        max_images: Maximum number of images to insert
        site_url: Base URL for image src (empty = relative path)

    Returns:
        Tuple of (modified_html, list_of_saved_filenames)
    """
    # Find all H2 positions
    h2_pattern = re.compile(r'(<h2[^>]*>.*?</h2>)', re.IGNORECASE | re.DOTALL)
    h2_matches = list(h2_pattern.finditer(article_html))

    if len(h2_matches) < 3:
        # Not enough sections to warrant inline images
        return article_html, []

    saved_files = []
    inserted = 0
    offset = 0  # Track position shift from insertions

    for i, match in enumerate(h2_matches):
        if inserted >= max_images:
            break
        # Insert after every 2nd H2 (index 1, 3, 5...)
        if i > 0 and i % 2 == 1:
            # Get the H2 heading text for context
            heading_text = re.sub(r'<[^>]+>', '', match.group(1)).strip()

            try:
                # Generate a contextual image for this section
                prompt = generate_smart_prompt(
                    api_key=api_key,
                    article_title=heading_text,
                    article_excerpt="",
                    keywords=[heading_text],
                    target="blog section illustration (wide, informative, related to the heading topic)",
                )

                image_bytes, provider = generate_image(
                    prompt=prompt,
                    api_key=api_key,
                    usage="inline",
                )

                # Save the image
                img_filename = f"{article_slug}-section-{inserted + 1}.png"
                output_dir.mkdir(parents=True, exist_ok=True)
                img_path = output_dir / img_filename
                img_path.write_bytes(image_bytes)
                saved_files.append(img_filename)

                # Build img tag
                if site_url:
                    img_src = f"{site_url.rstrip('/')}/images/{img_filename}"
                else:
                    img_src = f"/images/{img_filename}"

                img_tag = (
                    f'\n<figure style="text-align:center;margin:1.5em 0;">'
                    f'<img src="{img_src}" alt="{heading_text}" '
                    f'loading="lazy" width="800" height="450" '
                    f'style="max-width:100%;height:auto;border-radius:8px;" />'
                    f'</figure>\n'
                )

                # Insert the image tag right after the H2 heading
                # Find the end of the next paragraph after this H2
                insert_pos = match.end() + offset
                article_html = article_html[:insert_pos] + img_tag + article_html[insert_pos:]
                offset += len(img_tag)
                inserted += 1

                print(f"  📸 Inline image {inserted} inserted: {img_filename}")

            except Exception as e:
                print(f"  ⚠️ Failed to generate inline image for '{heading_text}': {e}")
                continue

    return article_html, saved_files


# ---------------------------------------------------------------------------
#  Utility: Extract slug from article filename
# ---------------------------------------------------------------------------

def extract_slug_from_filename(filename: str) -> str:
    """Extract the slug from an article filename, removing date prefix.

    Handles any date in YYYY-MM-DD format, not just hardcoded dates.
    """
    name = filename.replace(".md", "")
    # Remove YYYY-MM-DD_ prefix
    return re.sub(r'^\d{4}-\d{2}-\d{2}_', '', name)


# ---------------------------------------------------------------------------
#  Featured Image: Upload to WordPress
# ---------------------------------------------------------------------------

def upload_featured_image_wp(
    wp_url: str,
    auth: tuple,
    image_bytes: bytes,
    filename: str,
    title: str = "",
    alt_text: str = "",
) -> Optional[int]:
    """Upload an image to WordPress media library and return the media ID.

    Args:
        wp_url: WordPress site URL (e.g., 'https://example.com')
        auth: (username, app_password) tuple
        image_bytes: Raw image bytes
        filename: Filename for the uploaded media
        title: Optional title for the media item
        alt_text: Optional alt text for the media item

    Returns:
        Media ID if successful, None otherwise
    """
    try:
        media_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/media"

        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "image/png",
        }

        with httpx.Client(timeout=60) as client:
            resp = client.post(
                media_url,
                auth=auth,
                content=image_bytes,
                headers=headers,
            )

            if resp.status_code in (200, 201):
                media = resp.json()
                media_id = media.get("id")

                # Update alt text if provided
                if alt_text and media_id:
                    client.post(
                        f"{media_url}/{media_id}",
                        auth=auth,
                        json={"alt_text": alt_text},
                    )

                print(f"  ✅ Featured image uploaded: ID={media_id}")
                return media_id
            else:
                print(f"  ⚠️ Failed to upload media: HTTP {resp.status_code}: {resp.text[:200]}")
                return None

    except Exception as e:
        print(f"  ⚠️ Featured image upload error: {e}")
        return None


# ---------------------------------------------------------------------------
#  Main (CLI testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERRO: GEMINI_API_KEY não configurada")
        print("Use: export GEMINI_API_KEY=sua_chave")
        sys.exit(1)

    title = input("Título do artigo: ").strip() or "How to Build a Gaming PC in 2024"
    usage = input("Uso (pinterest/featured/inline/square): ").strip() or "pinterest"

    print(f"\n🎨 Gerando imagem para: {title}")
    print(f"   Uso: {usage}")

    try:
        image_bytes, provider, prompt = generate_article_image(
            api_key=api_key,
            article_title=title,
            usage=usage,
        )

        output_dir = Path(__file__).parent.parent / "images" / "generated"
        output_dir.mkdir(parents=True, exist_ok=True)

        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        filename = f"{usage}-{slug}.png"
        filepath = output_dir / filename
        filepath.write_bytes(image_bytes)

        print(f"\n✅ Sucesso!")
        print(f"   Provider: {provider}")
        print(f"   Prompt: {prompt[:100]}...")
        print(f"   Tamanho: {len(image_bytes) // 1024}KB")
        print(f"   Salvo em: {filepath}")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        sys.exit(1)
