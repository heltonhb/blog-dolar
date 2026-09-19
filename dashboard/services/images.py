# -*- coding: utf-8 -*-
"""Image prompt engineering and generation services."""
import re
from pathlib import Path

from dashboard.services.helpers import _env
from image_generator import generate_smart_prompt


def _build_pin_prompt(article_info: dict, usage: str = "pinterest") -> str:
    """Build an optimized image generation prompt for a pin/featured image.

    Uses the "Google Flow" approach: sends the article context to Gemini
    which generates a hyper-specific, visually rich prompt for the image
    generator. Falls back to a keyword-based prompt if Gemini is unavailable.
    """
    title = article_info.get("title", "")
    keywords = article_info.get("keywords", [])
    tags = article_info.get("tags", [])
    excerpt = article_info.get("excerpt", "")
    api_key = _env("GEMINI_API_KEY")

    if api_key:
        try:
            target_map = {
                "pinterest": "Pinterest pin (vertical 3:4, bold hero image for social media feed)",
                "featured": "blog featured hero banner (wide 16:9, editorial photography quality)",
                "inline": "blog section illustration (wide 16:9, informative, contextual)",
                "square": "social media square thumbnail (1:1, clean, bold focal point)",
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

    # Enhanced fallback: product-aware prompt building
    clean_kw = []
    for kw in (keywords + tags):
        cleaned = re.sub(r'^[\d\.\)]+\s*', '', kw).strip()
        cleaned = re.sub(r'^[A-Z]\.\s*', '', cleaned).strip()
        cleaned = re.sub(r'^(Phase|Step|Chapter)\s+\d+[:\.]?\s*', '', cleaned, flags=re.IGNORECASE).strip()
        words = cleaned.split()
        if 1 <= len(words) <= 4 and 3 < len(cleaned) < 35:
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
        "laptop": "sleek aluminum laptop on a minimalist wooden desk, warm ambient lighting, shallow depth of field",
        "monitor": "ultrawide curved monitor on a clean desk setup, subtle RGB glow, professional workspace",
        "headphone": "premium over-ear headphones resting on a leather surface, warm studio light, macro detail",
        "wifi": "modern mesh router with visible signal waves illustration, clean white surface, tech aesthetic",
        "build-a-pc": "PC components arranged in flat lay: motherboard, GPU, RAM sticks, on dark surface, studio lighting",
        "ssd": "NVMe SSD drive held at an angle showing the circuit board, macro photography, blue accent light",
        "vpn": "glowing digital shield hovering over a laptop, cybersecurity concept, dark teal and gold palette",
        "keyboard": "mechanical keyboard with custom keycaps, warm RGB backlighting, 45-degree angle, bokeh background",
        "mouse": "ergonomic gaming mouse on a large mousepad, dynamic lighting, close-up detail shot",
        "travel": "packed carry-on suitcase with travel essentials arranged around it, top-down flat lay, wanderlust mood",
        "pack": "organized packing cubes and travel gear flat lay on a bed, bright natural light",
        "privacy": "smartphone with a lock icon reflected on screen, moody dark lighting, privacy concept",
        "speed": "motion blur concept with digital speedometer, electric blue and white palette, dynamic energy",
        "fix": "precision tools and electronics on a repair workbench, macro close-up, workshop atmosphere",
        "guide": "organized desk with notebook, laptop and coffee, step-by-step learning concept, warm light",
        "best": "product lineup comparison on a clean gradient surface, studio lighting, top picks showcase",
        "budget": "wallet with money and a tech gadget, value proposition concept, warm tones",
        "gaming": "gaming setup with RGB peripherals and monitor, dark room with colorful lighting, immersive atmosphere",
        "work-from-home": "cozy home office with laptop, plant and coffee, natural window light, productive workspace",
        "nvme": "M.2 NVMe SSD installed on motherboard slot, macro photography with blue LED accent",
    }
    theme = next((desc for key, desc in theme_hints.items() if key in slug), "")
    kw_str = ", ".join(visual_kw)
    if theme:
        return (
            f"Professional editorial photography: {theme}. "
            f"Subject: {kw_str}. Shot with shallow depth of field, "
            f"soft directional lighting, clean composition. "
            f"No text, no words, no watermarks. Premium magazine quality."
        )
    return (
        f"Professional editorial photography of {kw_str}. "
        f"Shot at 45-degree angle with shallow depth of field, "
        f"soft directional lighting from the left, warm color temperature. "
        f"Clean modern surface, subtle bokeh background. "
        f"No text, no words, no watermarks. Magazine-quality composition."
    )
