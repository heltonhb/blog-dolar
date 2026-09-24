#!/usr/bin/env python3
"""Lista as URLs vivas dos posts do blog (sitemap de posts, via anti-bot)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from antibot import SITE, get_pagina  # noqa: E402


def fetch_post_urls(site: str = SITE) -> list[str]:
    """URLs de todos os posts, lendo o index e o sub-sitemap de posts."""
    index = get_pagina(f"{site}/wp-sitemap.xml")
    m = re.search(r"<loc>(https?://[^<]*wp-sitemap-posts-post-[^<]*)</loc>", index)
    alvo = m.group(1) if m else f"{site}/wp-sitemap-posts-post-1.xml"
    xml = get_pagina(alvo)
    return re.findall(r"<loc>(.*?)</loc>", xml)


if __name__ == "__main__":
    urls = fetch_post_urls()
    print(f"---{len(urls)} POSTS---")
    for u in urls:
        print(u)
