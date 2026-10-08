#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Pinterest Pin Variations — Blog em Dolar

Generates multiple high-converting Pinterest pin images (2:3 vertical aspect ratio)
with bold text overlays and rich Pinterest SEO metadata (titles, descriptions, bridge URLs)
tailored for Amazon buyer intent.

Usage:
    python3 scripts/generate_pin_variations.py --top-traction
    python3 scripts/generate_pin_variations.py --slug ssd-vs-hdd-storage-difference
    python3 scripts/generate_pin_variations.py --slug best-budget-laptops-for-students-2026
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Defina pollinations como padrão para geração em lote rápida se IMAGE_PROVIDER não estiver definido
if "IMAGE_PROVIDER" not in os.environ:
    os.environ["IMAGE_PROVIDER"] = "pollinations"

from image_generator import generate_image, add_pin_text_overlay
from dashboard.services.bridge import get_bridge_url

STATIC_IMAGES_DIR = PROJECT_ROOT / "dashboard" / "static" / "images"
DATA_DIR = PROJECT_ROOT / "dashboard" / "data"
OUTPUT_REGISTRY = DATA_DIR / "pin_variations.json"

# Definições curadas para os 3 artigos de maior tração comercial
TOP_TRACTION_PINS = {
    "ssd-vs-hdd-storage-difference": {
        "article_title": "SSD vs HDD Storage Difference: Which One Do You Really Need?",
        "variations": [
            {
                "variation": 1,
                "headline": "SSD VS HDD: WHICH TO BUY IN 2026?",
                "prompt": "Side by side comparison of a sleek NVMe SSD M.2 stick and an opened metallic computer hard disk drive, dramatic clean studio lighting, high tech hardware review aesthetic, vertical 2:3",
                "pin_title": "SSD vs HDD in 2026: Speed, Reliability & Buying Guide",
                "description": "Upgrading your computer storage? Discover the real-world speed differences between an SSD and a budget HDD, plus our top-rated SSD picks on Amazon. Check our full guide! #SSD #HDD #TechTips #PCUpgrade #Hardware",
            },
            {
                "variation": 2,
                "headline": "THE #1 FASTEST PC SPEED UPGRADE",
                "prompt": "Hands installing a high-speed NVMe PCIe 4.0 SSD into a modern motherboard with subtle RGB lighting, professional tech photography, crisp details, vertical 2:3",
                "pin_title": "The Fastest Speed Upgrade for Any PC or Laptop (SSD Guide)",
                "description": "Tired of slow boot times and lagging apps? Swapping an old hard drive for an SSD is the cheapest and most effective upgrade. Find the best budget SSDs on Amazon. #PCBuild #LaptopUpgrade #SSD #TechDeals",
            },
            {
                "variation": 3,
                "headline": "DON'T BUY STORAGE BEFORE THIS GUIDE",
                "prompt": "Top-down organized tech flat-lay featuring internal NVMe SSD, portable external SSD, and high-capacity backup hard drive on a dark matte desk, vertical 2:3",
                "pin_title": "SSD vs Hard Drive: Complete Price Per GB Breakdown (2026)",
                "description": "Should you buy a cheap 4TB HDD or a lightning-fast 1TB NVMe SSD? Read our breakdown of capacity vs speed and see the best verified Amazon recommendations. #TechHacks #Storage #SSDvsHDD",
            },
        ],
    },
    "best-budget-laptops-for-students-2026": {
        "article_title": "Best Budget Laptops for College Students in 2026",
        "variations": [
            {
                "variation": 1,
                "headline": "BEST STUDENT LAPTOPS UNDER $500",
                "prompt": "Modern lightweight laptop open on a sunlit wooden desk in college library student workspace",
                "pin_title": "Best Budget Laptops for College Students (Under $500 in 2026)",
                "description": "Looking for an affordable, reliable college laptop with all-day battery life? We tested the top budget models for homework, multitasking, and battery endurance on Amazon! #StudentLaptop #CollegeTech #BudgetLaptops #BackToSchool",
            },
            {
                "variation": 2,
                "headline": "TOP 5 COLLEGE LAPTOPS RANKED",
                "prompt": "Three modern slim budget laptops neatly displayed on a study table tech review",
                "pin_title": "Top 5 Student Laptops Ranked: Battery, Keyboard & Value",
                "description": "Don't overpay for college tech. Compare the Acer Aspire 5, Lenovo IdeaPad, and ASUS Vivobook with our verified buying guide and direct Amazon deals. #CollegeTips #LaptopReview #StudentDeals #TechGuide",
            },
            {
                "variation": 3,
                "headline": "ALL-DAY BATTERY ON A BUDGET",
                "prompt": "College student working with a sleek slim laptop at an outdoor campus cafe bright daylight",
                "pin_title": "Best College Laptops with All-Day Battery Life (2026 Buying Guide)",
                "description": "Need a college laptop that lasts through back-to-back classes without hunting for an outlet? Here are the top lightweight budget laptops on Amazon. #CollegeLife #TechGadgets #StudentHacks",
            },
        ],
    },
    "top-5-best-portable-power-banks-in-2026": {
        "article_title": "Top 5 Best Portable Power Banks in 2026: Fast Charging Tested",
        "variations": [
            {
                "variation": 1,
                "headline": "TOP 5 POWER BANKS TESTED (2026)",
                "prompt": "High-capacity power bank with bright LED display fast charging laptop and phone on desk",
                "pin_title": "Top 5 Best Portable Power Banks in 2026 (Laptop & Phone Fast Charging)",
                "description": "Never get stranded with a dead battery again. We tested high-speed power banks from Anker, Ugreen, and Baseus. Discover the best travel chargers on Amazon! #PowerBank #EDC #TravelGadgets #TechReviews",
            },
            {
                "variation": 2,
                "headline": "MUST-HAVE TRAVEL TECH GADGET",
                "prompt": "Minimalist flat-lay travel essentials ultra-slim power bank braided cables and phone",
                "pin_title": "Best Portable Chargers for Travel: Ultra-Slim & TSA Approved",
                "description": "Looking for a slim power bank that slips into your pocket or laptop sleeve and charges fast on long flights? Check out our top Amazon picks for travelers. #TravelTips #TravelEssentials #EDCGear",
            },
            {
                "variation": 3,
                "headline": "FAST CHARGE LAPTOPS ANYWHERE",
                "prompt": "Compact high-wattage power bank charging laptop at airport lounge table",
                "pin_title": "Best Laptop Power Banks (100W+ Fast Charging Guide 2026)",
                "description": "Can a portable power bank really charge your laptop at full speed? Yes! Check out the highest-rated 100W+ laptop chargers tested on Amazon. #RemoteWork #WFHGadgets #TechGuide",
            },
        ],
    },
    "top-5-amazon-tech-gadgets-under-30": {
        "article_title": "Top 5 Amazon Tech Gadgets Under $30 You Actually Need in 2026",
        "variations": [
            {
                "variation": 1,
                "headline": "5 AMAZON TECH GADGETS UNDER $30",
                "prompt": "Clean modern desk setup with compact phone charger, USB drive, and phone stand",
                "pin_title": "Top 5 Amazon Tech Gadgets Under $30 You Actually Need (2026)",
                "description": "Looking for smart, high-utility tech that won't break the bank? These 5 Amazon gadgets under $30 solve everyday headaches and last for years. Check out our tested picks! #AmazonFinds #TechGadgets #BudgetTech #EverydayCarry #AmazonDeals",
            },
            {
                "variation": 2,
                "headline": "UPGRADE YOUR DESK FOR UNDER $30",
                "prompt": "Minimalist clean computer desk setup with metallic phone stand and warm desk lamp",
                "pin_title": "Best Budget Desk Setup Upgrades Under $30 on Amazon",
                "description": "Transform your messy desk into a clean, productive minimalist workstation with these 5 affordable tech accessories under $30 on Amazon. #DeskSetup #WorkspaceInspo #WFHSetup #AmazonTech",
            },
            {
                "variation": 3,
                "headline": "BEST BUDGET TECH FINDS ON AMAZON",
                "prompt": "Tech accessories and electronic gadgets organized on modern wooden table",
                "pin_title": "The Most Useful Everyday Tech Essentials Under $30",
                "description": "Stop wasting money on cheap plastic accessories. These 5 Amazon tech essentials under $30 deliver immense daily value and durability. Read the full buyer guide! #EDCGear #TechEssentials #AmazonMustHaves #BestUnder30",
            },
        ],
    },
}


def load_registry() -> dict:
    if OUTPUT_REGISTRY.exists():
        try:
            return json.loads(OUTPUT_REGISTRY.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_registry(data: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_REGISTRY.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def generate_pins_for_slug(slug: str, api_key: str = "", force: bool = False) -> list[dict]:
    """Generates all pin variations for a given slug."""
    if slug not in TOP_TRACTION_PINS:
        print(f"❌ Slug '{slug}' não encontrado nas definições curadas.")
        return []

    item = TOP_TRACTION_PINS[slug]
    variations = item["variations"]
    STATIC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    bridge_url = get_bridge_url(slug)
    registry = load_registry()
    generated_pins = []

    print(f"\n=======================================================")
    print(f"📌 Gerando variações de Pins para: {slug}")
    print(f"🔗 Bridge URL: {bridge_url}")
    print(f"=======================================================")

    for var in variations:
        v_num = var["variation"]
        suffix = f"-v{v_num}" if v_num > 1 else ""
        filename = f"pin-{slug}{suffix}.png"
        filepath = STATIC_IMAGES_DIR / filename

        print(f"\n  🎨 Variação #{v_num} -> {filename}")
        print(f"  📝 Headline: \"{var['headline']}\"")
        print(f"  🎯 Pin Title: {var['pin_title']}")

        if filepath.exists() and not force:
            print(f"  📦 Arquivo já existe ({filepath.stat().st_size // 1024} KB). Pulando geração de imagem...")
            image_bytes = filepath.read_bytes()
            provider = "cached-local"
        else:
            print(f"  🧠 Prompt: {var['prompt'][:80]}...")
            raw_bytes, provider = generate_image(
                prompt=var["prompt"],
                api_key=api_key,
                usage="pinterest",
            )
            print(f"  ✍️ Adicionando overlay de texto...")
            image_bytes = add_pin_text_overlay(raw_bytes, var["headline"])
            filepath.write_bytes(image_bytes)
            print(f"  ✅ Salvo em: {filepath.name} ({len(image_bytes) // 1024} KB via {provider})")
            time.sleep(1)

        pin_meta = {
            "slug": slug,
            "variation": v_num,
            "filename": filename,
            "image_url": f"/static/images/{filename}",
            "headline": var["headline"],
            "pin_title": var["pin_title"],
            "description": var["description"],
            "bridge_url": bridge_url,
            "post_url": f"https://techtips.dpdns.org/{slug}/",
            "provider": provider,
            "size_kb": round(len(image_bytes) / 1024, 1),
        }
        generated_pins.append(pin_meta)

    # Atualiza registry
    registry[slug] = {
        "article_title": item["article_title"],
        "bridge_url": bridge_url,
        "pins": generated_pins,
    }
    save_registry(registry)
    return generated_pins


def main():
    parser = argparse.ArgumentParser(description="Generate Pinterest Pin Variations for Blog em Dólar")
    parser.add_argument("--slug", type=str, help="Slug do artigo para gerar")
    parser.add_argument("--top-traction", action="store_true", help="Gera os 3 artigos de maior tração")
    parser.add_argument("--force", action="store_true", help="Regera imagens mesmo se o arquivo já existir")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "")

    if args.slug:
        generate_pins_for_slug(args.slug, api_key=api_key, force=args.force)
    elif args.top_traction or not sys.argv[1:]:
        print("🚀 Gerando variações de Pins para todos os artigos de alta tração...")
        for slug in TOP_TRACTION_PINS:
            generate_pins_for_slug(slug, api_key=api_key, force=args.force)

    print("\n" + "=" * 60)
    print("🎉 Processo concluído com sucesso!")
    print(f"📄 Metadados salvos em: {OUTPUT_REGISTRY}")
    print("=" * 60)


if __name__ == "__main__":
    main()
