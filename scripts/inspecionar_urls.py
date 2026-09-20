#!/usr/bin/env python3
"""Inspeciona URLs individuais via Search Console URL Inspection API.

Retorna o veredito de indexação (PASS/FAIL/NEUTRAL), estado de cobertura
(INDEXED, NOT_INDEXED, DISCOVERED...), último crawl e motivos.
"""
import json
import sys
import urllib.request
import urllib.parse
import urllib.error

sys.path.insert(0, "scripts")
from check_indexacao import get_access_token

SITE = "https://tech-tips.ct.ws/"

URLS = [
    f"{SITE}",
    f"{SITE}privacy-policy/",
    f"{SITE}2026/08/31/hello-world/",
    f"{SITE}2026/09/19/top-essential-tech-tips-2026/",
    f"{SITE}2026/09/19/quantum-computing-2026/",
    f"{SITE}category/uncategorized/",
]


def inspect(token, url):
    body = json.dumps({
        "inspectionUrl": url,
        "siteUrl": SITE,
        "languageCode": "pt-BR",
    }).encode()
    req = urllib.request.Request(
        "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    token, _ = get_access_token("webmasters")
    for url in URLS:
        try:
            data = inspect(token, url)
            insp = data.get("inspectionResult", {})
            idx = insp.get("indexStatusResult", {})
            ver = idx.get("verdict", "?")
            cov = idx.get("coverageState", "?")
            last_crawl = idx.get("lastCrawlTime", "nunca")
            crawl_type = idx.get("crawledAs", "?")
            reasons = [r.get("reasons", []) for r in [idx] if r.get("reasons")]
            print(f"\n{url}")
            print(f"  veredito: {ver} | cobertura: {cov}")
            print(f"  último crawl: {last_crawl} | crawled as: {crawl_type}")
            if idx.get("reasons"):
                print(f"  motivos: {idx['reasons']}")
            page = insp.get("pageExperienceResult", {})
            print(f"  page experience: {page.get('verdict', '?')}")
        except urllib.error.HTTPError as e:
            print(f"\n{url}\n  ERRO {e.code}: {e.read().decode()[:200]}")
        except Exception as e:
            print(f"\n{url}\n  ERRO: {e}")


if __name__ == "__main__":
    main()
