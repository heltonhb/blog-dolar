#!/usr/bin/env python3
"""Saúde rápida do domínio novo: title/canonical/GA4/sitemap/robots."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from antibot import get_pagina  # noqa: E402

SITE = "https://techtips.dpdns.org"

h = get_pagina(f"{SITE}/")
t = re.search(r"<title>(.*?)</title>", h, re.S)
print("TITLE:", t.group(1).strip() if t else "?")
for pat in [r'<link rel="canonical" href="([^"]+)"',
            r'property="og:url" content="([^"]+)"',
            r'G-[A-Z0-9]{8,}',
            r'ct\.ws']:
    m = re.findall(pat, h)
    print(f"  {pat[:45]:48s} -> {m[:3] if m else 'AUSENTE'}")

s = get_pagina(f"{SITE}/sitemap.xml")
locs = re.findall(r"<loc>(.*?)</loc>", s)
print(f"SITEMAP locs={len(locs)} ct.ws={sum('ct.ws' in l for l in locs)}")
if locs:
    print("  ex.:", locs[0])

r = get_pagina(f"{SITE}/robots.txt")
print("ROBOTS:", repr(r[:200]))

a = get_pagina(f"{SITE}/ads.txt")
print("ADS.TXT:", repr(a[:200]))
