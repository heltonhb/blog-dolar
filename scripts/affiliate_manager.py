#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Affiliate Manager — Tech Tips (Blog em Dólar)

Injeta cartões de produto (Amazon Associates EUA) e o disclosure FTC/Amazon
nos artigos, tanto nos arquivos locais (articles/*.md) quanto nos posts VIVOS
do WordPress (via REST, atravessando o anti-bot da InfinityFree).

Princípios:
  * Idempotente: rodar de novo remove os cartões antigos e reinjeta — é assim
    que uma troca de tag (AMAZON_ASSOCIATE_TAG) chega a todos os posts.
  * Sem tag configurada → erro. Nunca publicar link com tag de outra pessoa.
  * HTML em linha única, com <p>/<ul> como filhos diretos do <div>: é o
    formato que o wpautop() do WordPress não quebra com <p>/<br> espúrios.
  * Sem logo da Amazon, sem preço e sem promessa de frete (Operating
    Agreement do Amazon Associates proíbe preço estático e uso de marca).

Uso:
    python3 scripts/affiliate_manager.py --scan
    python3 scripts/affiliate_manager.py --inject-all [--dry-run]           # arquivos locais
    python3 scripts/affiliate_manager.py --inject <arquivo.md> [--dry-run]
    python3 scripts/affiliate_manager.py --wp [--dry-run]                    # posts vivos
    python3 scripts/affiliate_manager.py --wp --slug <slug> [--dry-run]
    python3 scripts/affiliate_manager.py --check-wp                          # auditoria dos posts vivos
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTICLES_DIR = PROJECT_ROOT / "articles"
BACKUP_DIR = PROJECT_ROOT / "cache" / "affiliate_backups"

# Tags da Amazon US terminam em -20 (ex.: heltonhb-20).
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*-2\d$")


class ConfigError(RuntimeError):
    """Configuração ausente/inválida (ex.: AMAZON_ASSOCIATE_TAG)."""


def _env(name: str) -> str:
    """Lê do ambiente e, em fallback, do .env do projeto (sem depender do dotenv)."""
    val = os.environ.get(name, "").strip()
    if val:
        return val
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].split(" #", 1)[0].strip().strip("\"'")
    return ""


def get_amazon_tag() -> str:
    """Tag de afiliado da Amazon US. Falha alto se ausente ou malformada."""
    tag = _env("AMAZON_ASSOCIATE_TAG")
    if not tag:
        raise ConfigError("AMAZON_ASSOCIATE_TAG não definido no ambiente/.env")
    if not TAG_RE.match(tag):
        raise ConfigError(f"AMAZON_ASSOCIATE_TAG com formato inesperado: {tag!r} (esperado algo como 'seublog-20')")
    return tag


def generate_amazon_url(query_or_asin: str, tag: str) -> str:
    """Link de produto (ASIN) ou de busca na Amazon US, com a tag de afiliado."""
    q = query_or_asin.strip()
    if re.fullmatch(r"[A-Z0-9]{10}", q):
        return f"https://www.amazon.com/dp/{q}?tag={tag}"
    return f"https://www.amazon.com/s?k={quote_plus(q)}&tag={tag}"


# ─── Renderização ──────────────────────────────────────────────────────────
DISCLOSURE_TEXT = (
    "<strong>Affiliate Disclosure:</strong> Tech Tips is reader-supported. When you buy through "
    "links on our site, we may earn an affiliate commission at no additional cost to you. "
    "As an Amazon Associate, we earn from qualifying purchases."
)


def render_affiliate_disclosure() -> str:
    """Disclosure obrigatório (FTC + frase exigida pelo Amazon Associates)."""
    return f'<div class="tech-affiliate-disclosure"><p><small><em>{DISCLOSURE_TEXT}</em></small></p></div>'


def _card(
    *, title: str, subtitle: str, specs: list[str] | None, badge: str, url: str, cta: str,
    subtext: str, extra_class: str = "", btn_class: str = "amazon-btn", badge_class: str = "",
) -> str:
    esc = html.escape
    badge_html = f'<span class="affiliate-badge{badge_class}">{esc(badge)}</span> ' if badge else ""
    specs_html = ""
    if specs:
        specs_html = '<ul class="affiliate-specs">' + "".join(f"<li>{esc(s)}</li>" for s in specs) + "</ul>"
    return (
        f'<div class="tech-affiliate-card{extra_class}">'
        f'<p class="affiliate-card-header">{badge_html}<strong class="affiliate-title">{esc(title)}</strong></p>'
        f'<p class="affiliate-desc">{esc(subtitle)}</p>'
        f"{specs_html}"
        f'<p class="affiliate-action"><a href="{esc(url)}" target="_blank" rel="nofollow sponsored noopener" '
        f'class="affiliate-btn {btn_class}">{esc(cta)}</a> '
        f'<span class="affiliate-subtext">{esc(subtext)}</span></p>'
        f"</div>"
    )


def render_amazon_card(product: dict, tag: str) -> str:
    """Cartão de recomendação com botão para a Amazon."""
    url = generate_amazon_url(product.get("asin") or product["search_query"], tag)
    return _card(
        title=product["title"],
        subtitle=product["subtitle"],
        specs=product.get("specs"),
        badge=product.get("badge", "RECOMMENDED"),
        url=url,
        cta="Check Price on Amazon",
        subtext="Prices and availability change often",
    )


def render_vpn_card(product: dict, cta_url: str) -> str:
    """Cartão de VPN/SaaS (só usado quando há link de afiliado real configurado)."""
    provider = product.get("provider", "NordVPN")
    return _card(
        title=f"{product.get('headline', 'Recommended VPN')} ({provider})",
        subtitle="Protect your personal data across all your devices with strong encryption.",
        specs=product.get("specs"),
        badge=product.get("badge", ""),
        url=cta_url,
        cta=f"Get {provider}",
        subtext="30-day money-back guarantee",
        extra_class=" vpn-card",
        btn_class="vpn-btn",
        badge_class=" vpn-badge",
    )


def render_quick_recommendations(slug: str, tag: str, max_items: int = 3) -> str:
    """Caixa de recomendações rápidas acima da dobra (top escolhas). Linha única (wpautop-safe)."""
    products = get_products_for_slug(slug)
    if len(products) < 2:
        return ""
    items = products[:max_items]
    esc = html.escape
    items_html = []
    for p in items:
        if p.get("type") == "vpn":
            url = _env("NORDVPN_AFFILIATE_URL")
            if not url:
                continue
            btn_txt = f"Get {p.get('provider', 'VPN')}"
        else:
            url = generate_amazon_url(p.get("asin") or p["search_query"], tag)
            btn_txt = "Check Price on Amazon"

        badge = esc(p.get("badge", "TOP PICK"))
        title = esc(p["title"])
        subtitle = esc(p["subtitle"])
        items_html.append(
            f'<div class="quick-pick-item">'
            f'<div class="quick-pick-badge">{badge}</div>'
            f'<strong class="quick-pick-title">{title}</strong>'
            f'<p class="quick-pick-desc">{subtitle}</p>'
            f'<a href="{esc(url)}" target="_blank" rel="nofollow sponsored noopener" class="quick-pick-btn amazon-btn">{esc(btn_txt)} &rarr;</a>'
            f'</div>'
        )
    if not items_html:
        return ""
    cards_str = "".join(items_html)
    return (
        f'<div class="tech-quick-picks" data-affiliate="quick-picks">'
        f'<div class="quick-picks-header">'
        f'<span class="quick-picks-tag">⚡ AT A GLANCE</span>'
        f'<h3 class="quick-picks-title">Our Top Recommendations &amp; Quick Picks</h3>'
        f'</div>'
        f'<div class="quick-picks-grid">{cards_str}</div>'
        f'</div><!-- /tech-quick-picks -->'
    )


# Blocos gerados por este script (formato em linha única, ver render_*).
_CARD_RE = re.compile(r'\n?<div class="tech-affiliate-card[^"]*">.*?</p></div>\n?', re.DOTALL)
_QUICK_PICKS_RE = re.compile(r'\n?<div class="tech-quick-picks"[^>]*>.*?</div><!-- /tech-quick-picks -->\n?', re.DOTALL)
_DISCLOSURE_RE = re.compile(r'\n?<div class="tech-affiliate-disclosure">.*?</p></div>\n?', re.DOTALL)
# Formato legado (cartões multilinha com comentários) — não sabemos removê-lo com segurança.
_LEGACY_MARKERS = ("<!-- Affiliate Product Card Start -->", "<!-- Affiliate VPN Card Start -->")


def strip_affiliate_blocks(content: str) -> str:
    """Remove cartões, quick-picks e disclosure gerados anteriormente (reinjeção idempotente)."""
    content = _QUICK_PICKS_RE.sub("", content)
    content = _CARD_RE.sub("", content)
    return _DISCLOSURE_RE.sub("", content)


# ─── Mapeamento produto → seção do artigo (chave = slug do post) ───────────
# "after_heading": trecho do <h2>/<h3>; o cartão entra no FIM dessa seção
# (antes do próximo heading). Specs repetem só o que o próprio artigo afirma
# ou dados de fabricante verificáveis.
PRODUCTS: dict[str, list[dict]] = {
    "best-budget-laptops-for-students-2026": [
        {
            "after_heading": "Acer Aspire 5",
            "title": "Acer Aspire 5",
            "subtitle": "Best overall balance of price, performance and build quality for students.",
            "search_query": "Acer Aspire 5 laptop",
            "badge": "BEST OVERALL",
            "specs": ["USB-A, USB-C & HDMI ports", "Upgradeable storage", "Comfortable full-size keyboard"],
        },
        {
            "after_heading": "ASUS Vivobook Go 14",
            "title": "ASUS Vivobook Go 14",
            "subtitle": "Lightweight daily driver built for all-day battery life between classes.",
            "search_query": "ASUS Vivobook Go 14 laptop",
            "badge": "BEST BATTERY",
            "specs": ["All-day battery efficiency", "Lightweight chassis", "OLED screen option"],
        },
        {
            "after_heading": "Lenovo IdeaPad Slim 3",
            "title": "Lenovo IdeaPad Slim 3",
            "subtitle": "ThinkPad-inspired typing comfort at an entry-level price.",
            "search_query": "Lenovo IdeaPad Slim 3 16GB RAM laptop",
            "badge": "BEST VALUE",
            "specs": ["Great keyboard", "Physical webcam privacy shutter", "Look for the 16GB RAM config"],
        },
        {
            "after_heading": "Apple MacBook Air",
            "title": "Apple MacBook Air (M1 / M2)",
            "subtitle": "Silent fanless design with outstanding battery life and resale value.",
            "search_query": "Apple MacBook Air M2",
            "badge": "EDITOR'S CHOICE",
            "specs": ["Apple Silicon efficiency", "All-day battery life", "Premium aluminum build"],
        },
    ],
    "top-5-best-portable-power-banks-in-2026": [
        {
            "after_heading": "Anker Prime 27,650mAh",
            "title": "Anker Prime 27,650mAh Power Bank (250W)",
            "subtitle": "Charges a laptop, a tablet and a phone at the same time.",
            "search_query": "Anker Prime 27650mAh 250W power bank",
            "badge": "TOP PICK",
            "specs": ["27,650mAh capacity", "250W total output", "Smart display with battery stats"],
        },
        {
            "after_heading": "Baseus Blade 2",
            "title": "Baseus Blade Ultra-Slim Power Bank",
            "subtitle": "Thin enough to slide into a laptop sleeve — made for frequent flyers.",
            "search_query": "Baseus Blade power bank laptop",
            "badge": "SLIMMEST",
            "specs": ["Ultra-slim profile", "USB-C laptop fast charging", "Real-time status display"],
        },
        {
            "after_heading": "Ugreen Nexode 130W",
            "title": "UGREEN Nexode 130W Power Bank",
            "subtitle": "The sweet spot between price, capacity and size.",
            "search_query": "UGREEN Nexode power bank 130W",
            "badge": "BEST VALUE",
            "specs": ["Laptop-capable USB-C output", "Compact, daypack-friendly", "Multi-device charging"],
        },
        {
            "after_heading": "Shargeek Storm 2",
            "title": "Shargeek Storm 2 Power Bank",
            "subtitle": "Transparent design with adjustable output for tinkerers.",
            "search_query": "Shargeek Storm 2 power bank",
            "badge": "MOST UNIQUE",
            "specs": ["Transparent casing", "Adjustable voltage output", "Built-in info display"],
        },
        {
            "after_heading": "Samsung 25W Wireless",
            "title": "Samsung 25W Wireless Battery Pack (10,000mAh)",
            "subtitle": "Cable-free top-ups for your phone while you are on the go.",
            "search_query": "Samsung 25W wireless battery pack 10000mAh",
            "badge": "MOST CONVENIENT",
            "specs": ["10,000mAh capacity", "Wireless charging", "Pocket-friendly design"],
        },
    ],
    "best-monitors-work-from-home": [
        {
            "after_heading": "Dell UltraSharp U2724D",
            "title": "Dell UltraSharp U2724D 27\" QHD Monitor",
            "subtitle": "Productivity powerhouse with a 120Hz IPS Black panel and a USB-C hub.",
            "search_query": "Dell UltraSharp U2724D monitor",
            "badge": "BEST OVERALL",
            "specs": ["27-inch 2560x1440", "120Hz refresh rate", "USB-C hub connectivity"],
        },
        {
            "after_heading": "LG 34WN80C-B",
            "title": "LG 34WN80C-B 34\" Curved UltraWide",
            "subtitle": "21:9 screen real estate that replaces a dual-monitor setup.",
            "search_query": "LG 34WN80C-B ultrawide monitor",
            "badge": "BEST ULTRAWIDE",
            "specs": ["34-inch 3440x1440 IPS", "USB-C with 60W charging", "HDR10 support"],
        },
        {
            "after_heading": "ASUS ProArt Display PA278QV",
            "title": "ASUS ProArt PA278QV 27\" WQHD",
            "subtitle": "Factory-calibrated colors and an ergonomic stand at a budget price.",
            "search_query": "ASUS ProArt PA278QV monitor",
            "badge": "BEST BUDGET",
            "specs": ["27-inch 1440p IPS", "100% sRGB / Rec. 709", "Height, tilt, swivel & pivot"],
        },
    ],
    "nvme-ssd-vs-sata-ssd-vs-hdd": [
        {
            "after_heading": "When to Choose a SATA SSD",
            "title": "Samsung 870 EVO SATA SSD",
            "subtitle": "The easiest speed upgrade for older laptops and desktops with 2.5\" bays.",
            "search_query": "Samsung 870 EVO SATA SSD",
            "badge": "BEST SATA SSD",
            "specs": ["2.5-inch SATA III", "Up to 560 MB/s reads", "5-year limited warranty"],
        },
        {
            "after_heading": "When to Choose an NVMe SSD",
            "title": "Samsung 990 PRO NVMe SSD",
            "subtitle": "Top-tier PCIe 4.0 speeds for gaming and heavy creative workloads.",
            "search_query": "Samsung 990 PRO NVMe SSD",
            "badge": "FASTEST",
            "specs": ["PCIe 4.0 NVMe M.2", "Up to 7,450 MB/s reads", "5-year limited warranty"],
        },
        {
            "after_heading": "When to Choose an NVMe SSD",
            "title": "Crucial P3 Plus NVMe SSD",
            "subtitle": "Great value per gigabyte for laptop and desktop upgrades.",
            "search_query": "Crucial P3 Plus NVMe SSD",
            "badge": "BEST BUDGET NVMe",
            "specs": ["PCIe 4.0 NVMe M.2", "Up to 5,000 MB/s reads", "Micron 3D NAND"],
        },
    ],
    "ssd-vs-hdd-storage-difference": [
        {
            "after_heading": ["The Pros and Cons of SSDs", "When to Choose an NVMe SSD"],
            "title": "Samsung 990 PRO NVMe SSD",
            "subtitle": "Blazing fast PCIe 4.0 speeds (up to 7,450 MB/s) — the gold standard for gaming, booting, and heavy workloads.",
            "search_query": "Samsung 990 PRO NVMe SSD",
            "badge": "FASTEST PERFORMANCE",
            "specs": ["PCIe 4.0 NVMe M.2", "Up to 7,450 MB/s reads", "5-year limited warranty"],
        },
        {
            "after_heading": ["Choose an SSD if:", "What is an SSD"],
            "title": "Crucial P3 Plus NVMe SSD",
            "subtitle": "Unbeatable value per gigabyte for upgrading laptops or adding fast secondary game storage.",
            "search_query": "Crucial P3 Plus NVMe SSD",
            "badge": "BEST VALUE NVMe",
            "specs": ["PCIe 4.0 NVMe M.2", "Up to 5,000 MB/s reads", "Micron Advanced 3D NAND"],
        },
        {
            "after_heading": ["Choose an HDD if:", "The Pros and Cons of HDDs", "What is an HDD"],
            "title": "Seagate BarraCuda 4TB Internal Hard Drive",
            "subtitle": "Cost-effective massive bulk capacity for PC backups, media archives, and secondary storage.",
            "search_query": "Seagate BarraCuda 4TB Internal HDD",
            "badge": "BEST BULK STORAGE",
            "specs": ["3.5-inch SATA 6Gb/s", "5400 RPM / 256MB cache", "Great for media backups"],
        },
        {
            "after_heading": ["The Hybrid Approach", "When to Choose a SATA SSD"],
            "title": "Samsung 870 EVO SATA 2.5\" SSD",
            "subtitle": "The easiest and most reliable plug-and-play speed upgrade for older laptops and desktops with 2.5\" drive bays.",
            "search_query": "Samsung 870 EVO SATA SSD",
            "badge": "BEST 2.5\" SATA UPGRADE",
            "specs": ["2.5-inch SATA III", "Up to 560 MB/s reads", "Maxes out SATA interface"],
        },
    ],
    # VPN: só entra se NORDVPN_AFFILIATE_URL estiver configurado (link real de afiliado).
    "how-to-protect-your-digital-privacy-online": [
        {
            "type": "vpn",
            "after_heading": "Mask Your Connection with a VPN",
            "provider": "NordVPN",
            "headline": "Recommended VPN",
            "badge": "OUR PICK",
            "specs": ["Audited no-logs policy", "Blocks trackers & malicious ads", "30-day money-back guarantee"],
        }
    ],
    "best-noise-cancelling-headphones-2026": [
        {
            "after_heading": ["Sony WH-1000XM5", "Gold Standard", "Apex Pro"],
            "title": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
            "subtitle": "Industry-leading active noise cancellation with 8 microphones, Auto NC Optimizer, and high-res audio.",
            "search_query": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
            "badge": "BEST OVERALL ANC",
            "specs": ["Auto NC Optimizer", "Up to 30 hours battery life", "Crystal-clear hands-free calling"],
        },
        {
            "after_heading": ["Bose QuietComfort Ultra", "Comfort Champion", "SonicBeam"],
            "title": "Bose QuietComfort Ultra Wireless Headphones",
            "subtitle": "World-class quiet, breakthrough spatialized audio, and plush all-day physical comfort.",
            "search_query": "Bose QuietComfort Ultra Wireless Headphones",
            "badge": "MOST COMFORTABLE",
            "specs": ["CustomTune sound calibration", "Quiet, Aware & Immersion modes", "Luxury foldable design"],
        },
        {
            "after_heading": ["Anker Soundcore Space One", "Budget Monster", "Zenith Wireless"],
            "title": "Anker Soundcore Space One Noise Cancelling Headphones",
            "subtitle": "Outstanding 2X voice reduction and 55-hour playtime at an unbeatable budget price.",
            "search_query": "Anker Soundcore Space One Noise Cancelling Headphones",
            "badge": "BEST BUDGET VALUE",
            "specs": ["Adaptive active noise cancellation", "Up to 55 hours playtime", "Hi-Res Wireless Audio with LDAC"],
        },
    ],
    "step-by-step-custom-pc-building-guide": [
        {
            "after_heading": ["Installing Storage", "Core Components", "Phase 1: Planning and Compatibility", "Storage"],
            "title": "Crucial P3 Plus 1TB PCIe 4.0 NVMe SSD",
            "subtitle": "Blazing fast PCIe 4.0 M.2 storage (up to 5000 MB/s) — the ideal boot and game drive for custom PC builds.",
            "search_query": "Crucial P3 Plus 1TB PCIe 4.0 NVMe SSD",
            "badge": "RECOMMENDED STORAGE",
            "specs": ["M.2 2280 NVMe PCIe 4.0", "Up to 5000 MB/s read speed", "5-year limited warranty"],
        },
        {
            "after_heading": ["The Power Supply and Cable Management", "Power Supply", "PSU"],
            "title": "Corsair RM750e Fully Modular Power Supply (80+ Gold)",
            "subtitle": "Quiet, reliable 750W power delivery with modular cables for a clean, clutter-free build interior.",
            "search_query": "Corsair RM750e Power Supply Fully Modular 80 Gold",
            "badge": "BEST PSU",
            "specs": ["80 PLUS Gold certified", "Fully modular cables", "ATX 3.0 & PCIe 5.0 compliant"],
        },
        {
            "after_heading": ["Air Cooling vs. Liquid Cooling", "Air Cooling vs. Liquid Cooling", "Cooling"],
            "title": "ARCTIC MX-6 High-Performance Thermal Paste",
            "subtitle": "Easy-to-apply premium thermal compound providing exceptional heat transfer for CPUs and GPUs.",
            "search_query": "ARCTIC MX-6 Thermal Paste",
            "badge": "ESSENTIAL COMPOUND",
            "specs": ["Carbon micro-particle filler", "Non-conductive & non-capacitive", "Long-term durability"],
        },
        {
            "after_heading": ["Preparation and Tools", "Motherboard Prep", "Phase 2: The Assembly Process", "Tools"],
            "title": "iFixit Pro Tech Toolkit",
            "subtitle": "The industry standard precision screwdriver kit with all specialized bits needed to assemble PC hardware safely.",
            "search_query": "iFixit Pro Tech Toolkit PC Building",
            "badge": "ESSENTIAL TOOLKIT",
            "specs": ["64 precision screwdriver bits", "Anti-static wrist strap included", "Magnetic bit holder & opening tools"],
        },
    ],
    "how-to-choose-a-secure-password-manager": [
        {
            "after_heading": ["3. Extra Security Features", "Zero-Knowledge Architecture", "Key Factors"],
            "title": "Yubico YubiKey 5 NFC Hardware Security Key",
            "subtitle": "Eliminate account takeovers with the gold standard physical 2FA and passkey authenticator for USB-A and NFC.",
            "search_query": "Yubico YubiKey 5 NFC Security Key",
            "badge": "TOP HARDWARE 2FA",
            "specs": ["FIDO2 / WebAuthn & U2F compliant", "NFC touch for iPhone & Android", "Crush-resistant & water-resistant"],
        },
        {
            "after_heading": ["Cross-Platform Syncing", "Comparing Popular Security Models"],
            "title": "Yubico YubiKey 5C NFC Security Key (USB-C)",
            "subtitle": "Modern USB-C security key for laptops, tablets, and smartphones with lightning-fast tap-to-authenticate.",
            "search_query": "Yubico YubiKey 5C NFC USB-C Security Key",
            "badge": "BEST USB-C KEY",
            "specs": ["USB-C & NFC dual interface", "Multi-protocol authentication", "Hardware phishing defense"],
        },
    ],
    "top-essential-tech-tips-2026": [
        {
            "after_heading": ["Two-Factor Authentication", "2. Turn On Two-Factor Authentication Everywhere"],
            "title": "Yubico YubiKey 5 NFC Hardware Security Key",
            "subtitle": "The most effective hardware defense against phishing and password theft across all your online accounts.",
            "search_query": "Yubico YubiKey 5 NFC Security Key",
            "badge": "BEST 2FA DEFENSE",
            "specs": ["FIDO2 / WebAuthn standard", "NFC wireless & USB-A", "Works with Google, Apple, Microsoft"],
        },
        {
            "after_heading": ["Automate Your Backups", "3. Automate Your Backups Before You Need Them"],
            "title": "SanDisk 1TB Extreme Portable SSD",
            "subtitle": "Rugged, high-speed external USB-C drive for automated offline backups of photos, documents, and system images.",
            "search_query": "SanDisk 1TB Extreme Portable SSD USB-C",
            "badge": "BEST BACKUP DRIVE",
            "specs": ["Up to 1050MB/s read speeds", "IP65 water & dust resistance", "Compact carabiner loop design"],
        },
        {
            "after_heading": ["Secure Your Home Wi-Fi", "8. Secure Your Home Wi-Fi in 10 Minutes"],
            "title": "TP-Link RE700X Wi-Fi 6 Range Extender (AX3000)",
            "subtitle": "Boost your home network speed and eliminate dead zones with dual-band Wi-Fi 6 and gigabit Ethernet port.",
            "search_query": "TP-Link RE700X WiFi 6 Range Extender AX3000",
            "badge": "BEST WI-FI UPGRADE",
            "specs": ["AX3000 dual-band Wi-Fi 6", "Built-in Gigabit Ethernet port", "OneMesh smart roaming support"],
        },
    ],
    "how-to-fix-slow-wifi-troubleshooting-guide": [
        {
            "after_heading": ["Consider Upgrading Your Hardware", "When to Invest in a Mesh System", "Step 8"],
            "title": "TP-Link RE700X Wi-Fi 6 Mesh Range Extender",
            "subtitle": "Eliminate dead spots and expand ultra-fast gigabit wireless throughout your entire home or office.",
            "search_query": "TP-Link RE700X WiFi 6 Range Extender AX3000",
            "badge": "BEST WI-FI EXTENDER",
            "specs": ["Dual band AX3000 speeds", "Gigabit port for wired backhaul", "Universal router compatibility"],
        },
        {
            "after_heading": ["Router Placement", "Analyze Router Placement and Physical Obstacles", "Step 3"],
            "title": "Cat 8 Braided Gigabit Ethernet Cable (25ft)",
            "subtitle": "High-speed shielded network cable for low-latency gaming, streaming, and maximum throughput stability.",
            "search_query": "Cat 8 Braided Gigabit Ethernet Cable",
            "badge": "BEST WIRED CONNECTION",
            "specs": ["Up to 40Gbps transmission", "2000MHz bandwidth shielding", "Durable nylon braided exterior"],
        },
        {
            "after_heading": ["Isolate the Problem", "Step 2: Isolate the Problem", "Step 2"],
            "title": "TP-Link Archer TX20U Plus Wi-Fi 6 USB Adapter",
            "subtitle": "Instant Wi-Fi 6 upgrade for older laptops and desktops with high-gain dual antennas.",
            "search_query": "TP-Link Archer TX20U Plus WiFi 6 USB Adapter",
            "badge": "BEST PC ADAPTER",
            "specs": ["Dual high-gain antennas", "AX1800 speeds", "USB 3.0 plug and play"],
        },
    ],
    "how-to-speed-up-your-computer": [
        {
            "after_heading": ["Upgrade Your RAM", "Add More Memory", "RAM"],
            "title": "Corsair Vengeance LPX 16GB (2x8GB) DDR4 RAM",
            "subtitle": "Low-profile, high-performance desktop memory upgrade for responsive multitasking and smoother daily computing.",
            "search_query": "Corsair Vengeance LPX 16GB DDR4 RAM Desktop",
            "badge": "BEST RAM UPGRADE",
            "specs": ["3200MHz DDR4 speed", "Pure aluminum heat spreader", "Compatible with Intel and AMD"],
        },
        {
            "after_heading": ["Upgrade to an SSD", "Hard Drive vs SSD", "Storage"],
            "title": "Crucial P3 Plus 1TB PCIe 4.0 NVMe SSD",
            "subtitle": "Transform an agonizingly slow boot process into near-instantaneous load times with top-value PCIe 4.0 storage.",
            "search_query": "Crucial P3 Plus 1TB PCIe 4.0 NVMe SSD",
            "badge": "BEST SPEED UPGRADE",
            "specs": ["Up to 5000 MB/s sequential reads", "Micron Advanced 3D NAND", "5-year limited warranty"],
        },
        {
            "after_heading": ["Clean Out Dust", "Overheating", "Physical Maintenance"],
            "title": "Electric Compressed Air Duster for PC Cleaning",
            "subtitle": "Cordless, reusable high-power air blower to safely clear dust buildup from fans, keyboards, and PC cases.",
            "search_query": "Electric Compressed Air Duster PC Keyboard Cleaning",
            "badge": "ESSENTIAL CLEANING TOOL",
            "specs": ["Cordless rechargeable battery", "Up to 100,000 RPM motor", "Multiple precision nozzles included"],
        },
    ],
    "best-way-to-organize-digital-photos-across-devices": [
        {
            "after_heading": ["External Hard Drives", "Backup Strategy", "Physical Storage"],
            "title": "SanDisk 1TB Extreme Portable SSD",
            "subtitle": "Ultra-fast, rugged external SSD with up to 1050MB/s speeds for quick photo library backups and video editing.",
            "search_query": "SanDisk 1TB Extreme Portable SSD USB-C",
            "badge": "TOP BACKUP PICK",
            "specs": ["Up to 1050MB/s read speeds", "IP65 water & dust resistance", "USB-C and USB-A compatible"],
        },
        {
            "after_heading": ["Transferring Between Devices", "Mobile Backup", "Cloud vs Local"],
            "title": "SanDisk 128GB Ultra Dual Drive Luxe USB Type-C",
            "subtitle": "All-metal 2-in-1 flash drive with USB Type-C and Type-A connectors to easily move photos between phones and PCs.",
            "search_query": "SanDisk Ultra Dual Drive Luxe USB Type-C 128GB",
            "badge": "BEST PHONE TRANSFER DRIVE",
            "specs": ["Dual USB-C and USB-A connectors", "Up to 400MB/s transfer speeds", "All-metal swivel housing"],
        },
    ],
    "wifi-7-explained": [
        {
            "after_heading": ["Do You Actually Need to Upgrade Right Now?", "Upgrade Right Now"],
            "title": "TP-Link Archer BE550 Tri-Band Wi-Fi 7 Router",
            "subtitle": "Blazing-fast tri-band Wi-Fi 7 speeds up to 9214 Mbps with 2.5G ports and MLO technology.",
            "search_query": "TP-Link Archer BE550 WiFi 7 Router",
            "badge": "TOP WI-FI 7 ROUTER",
            "specs": ["Tri-band 9.2 Gbps Wi-Fi 7", "Five 2.5 Gbps ports", "Multi-Link Operation (MLO) support"],
        },
        {
            "after_heading": ["Practical Use Cases for WiFi 7", "Use Cases"],
            "title": "TP-Link Archer TBE550E Wi-Fi 7 PCIe Adapter",
            "subtitle": "Upgrade your desktop PC to next-gen Wi-Fi 7 and Bluetooth 5.4 with magnetic multi-directional antennas.",
            "search_query": "TP-Link Archer TBE550E WiFi 7 PCIe Card",
            "badge": "BEST PC WI-FI 7 UPGRADE",
            "specs": ["Tri-band BE9300 wireless", "Bluetooth 5.4 included", "Magnetic antenna base"],
        },
        {
            "after_heading": ["Wrapping Up Your Wireless Upgrade Journey", "Wrapping Up"],
            "title": "TP-Link Deco BE63 Mesh Wi-Fi 7 System (2-Pack)",
            "subtitle": "Whole-home Wi-Fi 7 coverage up to 5,000 sq ft eliminating dead zones with multi-gigabit mesh backhaul.",
            "search_query": "TP-Link Deco BE63 Mesh WiFi 7 System",
            "badge": "BEST WI-FI 7 MESH",
            "specs": ["Covers up to 5,000 sq. ft.", "Tri-band BE10000 mesh", "Four 2.5 Gbps ports per node"],
        },
    ],
}

# Aliases de slugs locais vs slugs do WordPress
PRODUCTS["how-to-build-a-pc-step-by-step-guide"] = PRODUCTS["step-by-step-custom-pc-building-guide"]
PRODUCTS["how-to-speed-up-windows-11-pc"] = PRODUCTS["how-to-speed-up-your-computer"]
PRODUCTS["how-to-fix-high-ping-and-packet-loss"] = PRODUCTS["how-to-fix-slow-wifi-troubleshooting-guide"]


def get_products_for_slug(slug: str) -> list[dict]:
    """Retorna produtos mapeados diretamente pelo slug ou por tópico/palavras-chave."""
    if slug in PRODUCTS:
        return PRODUCTS[slug]

    slug_lower = slug.lower()
    if any(k in slug_lower for k in ("headphone", "audio", "earbuds", "noise-cancelling")):
        return PRODUCTS.get("best-noise-cancelling-headphones-2026", [])
    if any(k in slug_lower for k in ("build-a-pc", "custom-pc", "pc-building")):
        return PRODUCTS.get("step-by-step-custom-pc-building-guide", [])
    if any(k in slug_lower for k in ("ssd", "hdd", "nvme", "storage", "hard-drive")):
        return PRODUCTS.get("ssd-vs-hdd-storage-difference") or PRODUCTS.get("nvme-ssd-vs-sata-ssd-vs-hdd", [])
    if any(k in slug_lower for k in ("laptop", "notebook", "ultrabook", "chromebook")):
        return PRODUCTS.get("best-budget-laptops-for-students-2026", [])
    if any(k in slug_lower for k in ("power-bank", "powerbank", "portable-charger", "battery-pack")):
        return PRODUCTS.get("top-5-best-portable-power-banks-in-2026", [])
    if any(k in slug_lower for k in ("monitor", "display", "screen", "work-from-home")):
        return PRODUCTS.get("best-monitors-work-from-home", [])
    if any(k in slug_lower for k in ("wifi", "wi-fi", "ping", "packet-loss", "network")):
        return PRODUCTS.get("how-to-fix-slow-wifi-troubleshooting-guide", [])
    if any(k in slug_lower for k in ("speed-up", "slow-pc", "slow-computer", "speed-up-windows")):
        return PRODUCTS.get("how-to-speed-up-your-computer", [])
    if any(k in slug_lower for k in ("photo", "backup", "photos")):
        return PRODUCTS.get("best-way-to-organize-digital-photos-across-devices", [])
    if any(k in slug_lower for k in ("password", "passwords", "security-key")):
        return PRODUCTS.get("how-to-choose-a-secure-password-manager", [])
    if any(k in slug_lower for k in ("privacy", "vpn", "cybersecurity")):
        return PRODUCTS.get("how-to-protect-your-digital-privacy-online", [])
    return []


_HEADING_RE = re.compile(r"<h[23][^>]*>", re.IGNORECASE)
_SECTION_STOP_RE = re.compile(r"<h[23][\s>]|<!-- internal-links -->", re.IGNORECASE)


def _insert_after_section(content: str, heading_text: str | list[str] | tuple[str, ...], block: str) -> tuple[str, bool]:
    """Insere `block` no fim da seção do heading que contém `heading_text` (ou lista de candidatos)."""
    candidates = [heading_text] if isinstance(heading_text, str) else list(heading_text)
    for cand in candidates:
        cand_lower = cand.lower()
        for m in _HEADING_RE.finditer(content):
            close = content.find("</h", m.end())
            if close == -1:
                continue
            inner = re.sub(r"<[^>]+>", "", content[m.end():close])
            if cand_lower in html.unescape(inner).lower():
                head_end = content.find(">", close) + 1
                stop = _SECTION_STOP_RE.search(content, head_end)
                pos = stop.start() if stop else len(content.rstrip())
                return content[:pos] + "\n" + block + "\n" + content[pos:], True

    # Fallback suave: insere antes de links internos ou conclusão se nenhum heading bateu
    stop = re.search(r"<!-- internal-links -->|<h2[^>]*>.*?(?:conclusion|verdict|final thoughts)", content, re.IGNORECASE)
    if stop:
        pos = stop.start()
        return content[:pos] + "\n" + block + "\n" + content[pos:], True

    return content, False


def build_blocks(slug: str, tag: str) -> tuple[list[tuple[str, str]], list[str]]:
    """[(after_heading, html)] para o slug, + avisos (itens pulados)."""
    blocks, warnings = [], []
    products = get_products_for_slug(slug)
    for product in products:
        if product.get("type") == "vpn":
            url = _env("NORDVPN_AFFILIATE_URL")
            if not url:
                warnings.append(f"VPN ({product.get('provider')}) pulado: NORDVPN_AFFILIATE_URL não configurado")
                continue
            blocks.append((product["after_heading"], render_vpn_card(product, url)))
        else:
            blocks.append((product["after_heading"], render_amazon_card(product, tag)))
    return blocks, warnings


def apply_affiliate_content(
    content: str,
    slug: str,
    tag: str,
    *,
    has_frontmatter: bool = False,
    include_quick_picks: bool = True,
) -> tuple[str, list[str]]:
    """Remove blocos antigos e injeta cartões + quick-picks + disclosure. Retorna (conteúdo, avisos)."""
    if any(mk in content for mk in _LEGACY_MARKERS):
        raise ValueError("conteúdo contém cartões no formato legado — restaure o original antes")

    content = strip_affiliate_blocks(content)
    blocks, warnings = build_blocks(slug, tag)
    if not blocks:
        return content, warnings + ["nenhum cartão aplicável — conteúdo mantido sem disclosure"]

    for heading, block in blocks:
        content, ok = _insert_after_section(content, heading, block)
        if not ok:
            warnings.append(f"heading não encontrado: {heading!r} — cartão NÃO inserido")

    if "tech-affiliate-card" not in content:
        return strip_affiliate_blocks(content), warnings

    if include_quick_picks:
        quick_box = render_quick_recommendations(slug, tag)
        if quick_box:
            inserted = False
            m_intro = re.search(r'<h[23][^>]*>.*?(?:intro|introduction).*?</h[23]>', content, re.IGNORECASE)
            if m_intro:
                m_next = re.search(r'<h2[\s>]', content[m_intro.end():], re.IGNORECASE)
                if m_next:
                    pos = m_intro.end() + m_next.start()
                    content = content[:pos] + "\n" + quick_box + "\n" + content[pos:]
                    inserted = True
            if not inserted:
                m_first = re.search(r'<h2[\s>]', content, re.IGNORECASE)
                if m_first:
                    pos = m_first.start()
                    content = content[:pos] + "\n" + quick_box + "\n" + content[pos:]
                    inserted = True
            if not inserted:
                stop = re.search(r'<!-- internal-links -->', content, re.IGNORECASE)
                pos = stop.start() if stop else len(content)
                content = content[:pos] + "\n" + quick_box + "\n" + content[pos:]

    disclosure = render_affiliate_disclosure()
    fm = re.match(r"---\n.*?\n---\n", content, re.DOTALL) if has_frontmatter else None
    if fm:
        content = content[: fm.end()] + "\n" + disclosure + "\n" + content[fm.end():]
    else:
        content = disclosure + "\n" + content
    return content, warnings


# ─── Arquivos locais ───────────────────────────────────────────────────────
def _slug_of(path: Path) -> str:
    m = re.search(r"^slug:\s*(\S+)", path.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
    return m.group(1).strip("\"'") if m else re.sub(r"^\d{4}-\d{2}-\d{2}_", "", path.stem)


def _local_files() -> dict[str, Path]:
    return {_slug_of(p): p for p in sorted(ARTICLES_DIR.glob("*.md"))}


def scan_articles() -> list[dict]:
    """Status de monetização dos artigos locais."""
    out = []
    for slug, path in _local_files().items():
        content = path.read_text(encoding="utf-8", errors="ignore")
        out.append({
            "filename": path.name,
            "slug": slug,
            "mapped": len(PRODUCTS.get(slug, [])),
            "cards": content.count("tech-affiliate-card"),
        })
    return out


def inject_local(path: Path, tag: str, dry_run: bool = False) -> bool:
    slug = _slug_of(path)
    if slug not in PRODUCTS:
        print(f"[!] sem mapeamento para {path.name} (slug={slug})")
        return False
    original = path.read_text(encoding="utf-8")
    new, warnings = apply_affiliate_content(original, slug, tag, has_frontmatter=True)
    for w in warnings:
        print(f"    ⚠️ {w}")
    n = new.count("tech-affiliate-card")
    if new == original:
        print(f"[=] {path.name}: sem alterações")
        return False
    if dry_run:
        print(f"[DRY-RUN] {path.name}: {n} cartões")
        return True
    path.write_text(new, encoding="utf-8")
    print(f"[+] {path.name}: {n} cartões + disclosure")
    return True


# ─── WordPress (posts vivos) ───────────────────────────────────────────────
def _wp():
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    from antibot import SITE  # noqa: E402
    from fetch_wp_post import _rest_get  # noqa: E402
    from internal_links import _atualizar_post  # noqa: E402

    return SITE, _rest_get, _atualizar_post


def _wp_list_posts(rest_get, site: str) -> list[dict]:
    """Lista metadados leves de todos os posts (id, slug, link)."""
    raw = rest_get(f"{site}/wp-json/wp/v2/posts?per_page=100&_fields=id,slug,link")
    return json.loads(raw)


def _wp_get_post(rest_get, site: str, post_id: int) -> dict:
    """Carrega o conteúdo editável de um post específico."""
    raw = rest_get(f"{site}/wp-json/wp/v2/posts/{post_id}?context=edit&_fields=id,slug,link,content")
    return json.loads(raw)


def _wp_posts(rest_get, site: str) -> list[dict]:
    """Compatibilidade: carrega todos os posts com conteúdo em lote (apenas metadados + conteúdo por post se necessário)."""
    metas = _wp_list_posts(rest_get, site)
    full = []
    for m in metas:
        try:
            full.append(_wp_get_post(rest_get, site, m["id"]))
        except Exception as e:
            print(f"⚠️ Erro ao carregar post {m['id']}: {e}")
    return full


def inject_wp(tag: str, only_slug: str | None = None, dry_run: bool = False) -> int:
    site, rest_get, put = _wp()
    posts_meta = {p["slug"]: p for p in _wp_list_posts(rest_get, site)}
    targets = [only_slug] if only_slug else list(PRODUCTS)
    updated = 0
    for slug in targets:
        meta = posts_meta.get(slug)
        if not meta:
            print(f"[-] {slug}: não publicado no WordPress — pulando")
            continue
        post = _wp_get_post(rest_get, site, meta["id"])
        raw = post["content"]["raw"]
        new, warnings = apply_affiliate_content(raw, slug, tag)
        for w in warnings:
            print(f"    ⚠️ {w}")
        n = new.count("tech-affiliate-card")
        if new == raw:
            print(f"[=] {slug}: já está atualizado ({n} cartões)")
            continue
        if dry_run:
            print(f"[DRY-RUN] {slug} (post {post['id']}): {n} cartões")
            continue
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        bak = BACKUP_DIR / f"{slug}-{time.strftime('%Y%m%d-%H%M%S')}.html"
        bak.write_text(raw, encoding="utf-8")
        if put(post["id"], new):
            updated += 1
            print(f"[+] {slug} (post {post['id']}): {n} cartões + disclosure  (backup: {bak.relative_to(PROJECT_ROOT)})")
        else:
            print(f"[✗] {slug}: falha no PUT (backup em {bak.relative_to(PROJECT_ROOT)})")
    return updated


def check_wp(tag: str) -> bool:
    """Audita os posts vivos: tag correta, rel sponsored e disclosure presentes."""
    site, rest_get, _ = _wp()
    ok = True
    posts_meta = _wp_list_posts(rest_get, site)
    for meta in posts_meta:
        # Apenas audita posts com produtos mapeados ou posts gerais
        p = _wp_get_post(rest_get, site, meta["id"])
        c = p["content"]["raw"]
        links = re.findall(r'<a [^>]*href="(https://www\.amazon\.com/[^"]+)"[^>]*>', c)
        if not links:
            continue
        tags = set(re.findall(r"tag=([\w-]+)", html.unescape(" ".join(links))))
        anchors = re.findall(r'<a [^>]*href="https://www\.amazon\.com/[^"]+"[^>]*>', c)
        sponsored = all('rel="nofollow sponsored' in a for a in anchors)
        disclosed = "As an Amazon Associate, we earn from qualifying purchases" in c
        good = tags == {tag} and sponsored and disclosed
        ok &= good
        print(f"[{'OK' if good else 'ERRO'}] {p['slug']}: {len(links)} links, tags={sorted(tags)}, "
              f"sponsored={sponsored}, disclosure={disclosed}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="Affiliate Manager — Tech Tips")
    ap.add_argument("--scan", action="store_true", help="status dos artigos locais")
    ap.add_argument("--inject", metavar="ARQUIVO", help="injeta em um arquivo de articles/")
    ap.add_argument("--inject-all", "--inject-sample", dest="inject_all", action="store_true",
                    help="injeta em todos os artigos locais mapeados")
    ap.add_argument("--wp", action="store_true", help="injeta nos posts vivos do WordPress")
    ap.add_argument("--slug", help="com --wp: limita a um post")
    ap.add_argument("--check-wp", action="store_true", help="audita links de afiliado nos posts vivos")
    ap.add_argument("--dry-run", action="store_true", help="não grava nada")
    args = ap.parse_args()

    if args.scan:
        for s in scan_articles():
            status = "ATIVO" if s["cards"] else ("PRONTO" if s["mapped"] else "-")
            print(f"[{status:<6}] {s['filename']}  (mapeados: {s['mapped']}, no arquivo: {s['cards']})")
        return 0

    try:
        tag = get_amazon_tag()
    except ConfigError as e:
        print(f"❌ {e}")
        return 2

    if args.check_wp:
        return 0 if check_wp(tag) else 1
    if args.wp:
        inject_wp(tag, args.slug, args.dry_run)
        return 0
    if args.inject:
        inject_local(ARTICLES_DIR / args.inject, tag, args.dry_run)
        return 0
    if args.inject_all:
        files = _local_files()
        for slug in PRODUCTS:
            if slug in files:
                inject_local(files[slug], tag, args.dry_run)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
