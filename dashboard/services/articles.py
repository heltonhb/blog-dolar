# -*- coding: utf-8 -*-
"""Article parsing and content extraction services."""
import re
from pathlib import Path


def _extract_article_info(filepath: Path) -> dict:
    """Extract frontmatter and structural metadata from a Markdown article."""
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
