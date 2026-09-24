#!/usr/bin/env python3
"""Diagnóstico: o conteúdo do post na REST contém o bloco internal-links?"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch_wp_post import fetch_post_by_slug  # noqa: E402

post = fetch_post_by_slug("how-to-learn-git-version-control")
c = post["content_html"]
print(f"tamanho: {len(c)}")
print(f"tem 'Related Articles': {'Related Articles' in c}")
print(f"tem 'internal-links': {'internal-links' in c}")
print(f"fim do conteúdo: {c[-300:]!r}")
