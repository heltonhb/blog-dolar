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


# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

ASPECT_RATIOS = {
    "pinterest": "3:4",     # Vertical pin (ideal for Pinterest)
    "featured": "16:9",     # Wide banner for WordPress featured image
    "inline": "16:9",       # Wide image for article body
    "square": "1:1",        # Square fallback
}

# Dimensions for Pollinations fallback (which uses width/height, not aspect ratio)
DIMENSIONS = {
    "pinterest": (768, 1024),
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
    model: str = "gemini-flash-lite-latest",
) -> str:
    """Use Gemini text model to create an optimal image generation prompt.

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
    kw_str = ", ".join(keywords[:5]) if keywords else ""
    excerpt_part = f"\nArticle excerpt: {article_excerpt[:400]}" if article_excerpt else ""

    prompt = f"""You are an expert image prompt engineer for AI image generation.
Based on this blog article, create a single highly specific image generation prompt
for a {target}.

Article title: {article_title}{excerpt_part}
Keywords: {kw_str}

Requirements for the image prompt you generate:
- Describe a visually striking, photorealistic or high-quality illustration scene
- Must be directly and obviously related to the article's main topic
- Specify concrete visual elements (objects, colors, composition, lighting)
- NO text, NO words, NO letters, NO watermarks in the image
- Bright, eye-catching colors suitable for social media
- One clear focal subject with clean composition
- Professional, editorial quality

Return ONLY the image prompt text, nothing else. No quotes, no explanation."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 250},
    }

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return result.strip().strip('"').strip("'")
    except Exception as e:
        # Fallback to simple prompt
        print(f"  ⚠️ Smart prompt generation failed ({e}), using fallback")
        return _build_fallback_prompt(article_title, keywords or [])


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
        f"Vibrant professional illustration about {subject}. "
        f"Colorful modern editorial style, bright gradient background, "
        f"clean composition, detailed, sharp, high quality. "
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
    """Generate an image using Google Gemini Imagen API (free tier).

    Args:
        api_key: Gemini API key
        prompt: Image generation prompt
        aspect_ratio: One of '1:1', '3:4', '4:3', '9:16', '16:9'
        model: Imagen model to use

    Returns:
        Raw image bytes (PNG)

    Raises:
        RuntimeError: If image generation fails after retries
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            "personGeneration": "dont_allow",
        },
    }

    last_err = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=90) as client:
                resp = client.post(url, json=payload)

                if resp.status_code in (429, 503):
                    wait = 5 * (attempt + 1)
                    print(f"  ⏳ Gemini Imagen rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    last_err = f"HTTP {resp.status_code}"
                    continue

                resp.raise_for_status()
                data = resp.json()

            predictions = data.get("predictions", [])
            if not predictions:
                raise ValueError("No predictions returned from Imagen API")

            image_b64 = predictions[0].get("bytesBase64Encoded", "")
            if not image_b64:
                raise ValueError("No image data in prediction response")

            image_bytes = base64.b64decode(image_b64)

            # Validate it's a real image (minimum size check)
            if len(image_bytes) < 5000:
                raise ValueError(f"Image too small ({len(image_bytes)} bytes), likely invalid")

            return image_bytes

        except Exception as e:
            last_err = str(e)
            if attempt < 2:
                time.sleep(3 * (attempt + 1))

    raise RuntimeError(f"Gemini Imagen failed after 3 attempts: {last_err}")


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

    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={seed}"

    with httpx.Client(timeout=90, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()

    if len(resp.content) < 5000:
        raise ValueError(f"Pollinations returned too-small image ({len(resp.content)} bytes)")

    return resp.content


# ---------------------------------------------------------------------------
#  Multi-provider Fallback
# ---------------------------------------------------------------------------

def generate_image(
    prompt: str,
    api_key: str = "",
    usage: str = "pinterest",
    **kwargs,
) -> tuple[bytes, str]:
    """Generate an image using the best available provider.

    Tries Gemini Imagen first, then falls back to Pollinations.ai.

    Args:
        prompt: Image generation prompt
        api_key: Gemini API key (required for Gemini, optional for Pollinations fallback)
        usage: Target usage - 'pinterest', 'featured', 'inline', or 'square'

    Returns:
        Tuple of (image_bytes, provider_name)
    """
    providers = []

    # Gemini Imagen (best quality) - needs API key
    if api_key:
        aspect = ASPECT_RATIOS.get(usage, "1:1")
        providers.append({
            "name": "gemini-imagen",
            "fn": lambda p: generate_image_gemini(api_key, p, aspect_ratio=aspect),
        })

    # Pollinations (fallback - no API key needed)
    w, h = DIMENSIONS.get(usage, (1024, 1024))
    providers.append({
        "name": "pollinations",
        "fn": lambda p: generate_image_pollinations(p, width=w, height=h),
    })

    last_err = None
    for provider in providers:
        try:
            print(f"  🎨 Tentando {provider['name']}...")
            image_bytes = provider["fn"](prompt)
            if len(image_bytes) > 5000:
                print(f"  ✅ Imagem gerada via {provider['name']} ({len(image_bytes) // 1024}KB)")
                return image_bytes, provider["name"]
        except Exception as e:
            last_err = str(e)
            print(f"  ⚠️ {provider['name']} falhou: {e}")
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
        "pinterest": "Pinterest pin (vertical 3:4 ratio, eye-catching)",
        "featured": "blog featured hero image (wide 16:9 ratio, professional)",
        "inline": "blog section illustration (wide 16:9 ratio, informative)",
        "square": "social media square image (1:1 ratio)",
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

    # Generate the image
    image_bytes, provider = generate_image(
        prompt=prompt,
        api_key=api_key,
        usage=usage,
    )

    return image_bytes, provider, prompt


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
