# -*- coding: utf-8 -*-
"""Tests for scripts/affiliate_manager.py (pure functions only — no network)."""
import importlib.util
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parent.parent / "scripts" / "affiliate_manager.py"
_spec = importlib.util.spec_from_file_location("affiliate_manager", _PATH)
am = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(am)

TAG = "testblog-20"

POST = """<p>Intro paragraph.</p>
<h2>Top Picks: The Best Budget Laptops for Students 2026</h2>
<p>We tested them.</p>
<h3>1. The All-Around Champion: Acer Aspire 5 (2026 Edition)</h3>
<p>Great laptop.</p>
<ul>
<li>Pros: ports</li>
</ul>
<h3>2. The Battery Life King: ASUS Vivobook Go 14</h3>
<p>Long battery.</p>
<h3>3. The Premium Feel on a Dime: Lenovo IdeaPad Slim 3</h3>
<p>Nice keyboard.</p>
<h3>4. The Apple Alternative: Apple MacBook Air (M1 or Base M2 Refurbished/Sale)</h3>
<p>Fanless.</p>
<h2>Final Verdict</h2>
<p>Pick one.</p>
<!-- internal-links -->
<h3>Related Articles</h3>
<ul><li><a href="/x">X</a></li></ul>
<!-- /internal-links -->
"""
SLUG = "best-budget-laptops-for-students-2026"


def test_tag_is_required(monkeypatch, tmp_path):
    monkeypatch.delenv("AMAZON_ASSOCIATE_TAG", raising=False)
    monkeypatch.setattr(am, "PROJECT_ROOT", tmp_path)  # sem .env
    with pytest.raises(am.ConfigError):
        am.get_amazon_tag()


def test_tag_format_validated(monkeypatch):
    monkeypatch.setenv("AMAZON_ASSOCIATE_TAG", "not a tag")
    with pytest.raises(am.ConfigError):
        am.get_amazon_tag()
    monkeypatch.setenv("AMAZON_ASSOCIATE_TAG", TAG)
    assert am.get_amazon_tag() == TAG


def test_urls_carry_tag():
    assert am.generate_amazon_url("B0ABCDEFGH", TAG) == f"https://www.amazon.com/dp/B0ABCDEFGH?tag={TAG}"
    assert am.generate_amazon_url("Acer Aspire 5", TAG) == f"https://www.amazon.com/s?k=Acer+Aspire+5&tag={TAG}"


def test_card_is_compliant_and_wpautop_safe():
    card = am.render_amazon_card(am.PRODUCTS[SLUG][0], TAG)
    assert "\n" not in card  # linha única: wpautop não injeta <br>/<p>
    assert 'rel="nofollow sponsored noopener"' in card
    assert f"tag={TAG}" in card
    assert "&amp;tag=" in card  # & escapado no atributo
    assert "<svg" not in card and "Prime" not in card and "$" not in card


def test_inject_places_cards_in_their_sections():
    out, warnings = am.apply_affiliate_content(POST, SLUG, TAG)
    assert warnings == []
    assert out.startswith('<div class="tech-affiliate-disclosure">')
    assert out.count("tech-affiliate-card") == 4
    # cada cartão fica antes do heading seguinte e antes do bloco de links internos
    acer = out.index("Check Price", out.index("Acer Aspire 5 (2026"))
    assert acer < out.index("2. The Battery Life King")
    mac = out.index('<strong class="affiliate-title">Apple MacBook Air')
    assert out.index("4. The Apple Alternative") < mac < out.index("<h2>Final Verdict")
    assert out.index("<!-- internal-links -->") > mac


def test_inject_is_idempotent_and_strip_restores_original():
    once, _ = am.apply_affiliate_content(POST, SLUG, TAG)
    twice, _ = am.apply_affiliate_content(once, SLUG, TAG)
    assert once == twice
    assert am.strip_affiliate_blocks(once) == POST


def test_retag_replaces_old_tag():
    old, _ = am.apply_affiliate_content(POST, SLUG, "old-20")
    new, _ = am.apply_affiliate_content(old, SLUG, TAG)
    # 4 cartões de seção + 3 quick picks no topo = 7 links de afiliado
    assert "tag=old-20" not in new and new.count(f"tag={TAG}") == 7


def test_quick_recommendations_wpautop_safe():
    box = am.render_quick_recommendations(SLUG, TAG)
    assert "\n" not in box  # linha única: wpautop-safe
    assert 'class="tech-quick-picks"' in box
    assert box.count('class="quick-pick-item"') == 3
    assert 'rel="nofollow sponsored noopener"' in box
    assert f"tag={TAG}" in box


def test_quick_recommendations_skipped_for_single_or_empty():
    assert am.render_quick_recommendations("how-to-protect-your-digital-privacy-online", TAG) == ""
    assert am.render_quick_recommendations("non-existent-slug", TAG) == ""


def test_missing_heading_is_reported_not_appended():
    out, warnings = am.apply_affiliate_content("<p>nothing here</p>\n", SLUG, TAG)
    assert out == "<p>nothing here</p>\n"  # sem cartões → sem disclosure
    assert len(warnings) == 4


def test_vpn_card_skipped_without_real_affiliate_url(monkeypatch):
    monkeypatch.setenv("NORDVPN_AFFILIATE_URL", "")
    monkeypatch.setattr(am, "_env", lambda name: "")
    post = "<h2>Step 3: Mask Your Connection with a VPN</h2>\n<p>Use one.</p>\n"
    out, warnings = am.apply_affiliate_content(post, "how-to-protect-your-digital-privacy-online", TAG)
    assert out == post
    assert any("NORDVPN_AFFILIATE_URL" in w for w in warnings)


def test_frontmatter_kept_on_top():
    md = "---\ntitle: X\nslug: " + SLUG + "\n---\n" + POST
    out, _ = am.apply_affiliate_content(md, SLUG, TAG, has_frontmatter=True)
    assert out.startswith("---\ntitle: X\n")
    assert out.index("tech-affiliate-disclosure") > out.index("\n---\n")
    assert am.strip_affiliate_blocks(out) == md


def test_legacy_format_refused():
    with pytest.raises(ValueError):
        am.apply_affiliate_content("<!-- Affiliate Product Card Start -->x", SLUG, TAG)


def test_dynamic_catalog_save_and_load(monkeypatch, tmp_path):
    monkeypatch.setattr(am, "PROJECT_ROOT", tmp_path)
    custom_slug = "best-mechanical-keyboards-2026"
    products = [
        {
            "title": "Keychron K2 Wireless Mechanical Keyboard",
            "subtitle": "Compact 75% layout with hot-swappable switches and Bluetooth connectivity.",
            "search_query": "Keychron K2 Mechanical Keyboard",
            "badge": "BEST WIRELESS KEYBOARD",
            "after_heading": "Keychron K2",
            "specs": ["Bluetooth & Wired", "Hot-swappable", "Mac & Windows layout"],
        },
        {
            "title": "Logitech MX Mechanical Mini",
            "subtitle": "Low-profile mechanical switches for quiet and ergonomic typing.",
            "search_query": "Logitech MX Mechanical Mini",
            "badge": "BEST LOW PROFILE",
            "after_heading": "Logitech MX Mechanical",
            "specs": ["Tactile quiet switches", "Smart illumination", "Multi-device flow"],
        },
    ]

    am.save_custom_products(custom_slug, products)
    catalog = am.load_custom_products()
    assert custom_slug in catalog
    assert len(catalog[custom_slug]) == 2
    assert catalog[custom_slug][0]["title"] == "Keychron K2 Wireless Mechanical Keyboard"

    loaded_products = am.get_products_for_slug(custom_slug)
    assert len(loaded_products) == 2
    assert loaded_products[0]["search_query"] == "Keychron K2 Mechanical Keyboard"


def test_dynamic_catalog_prioritizes_custom_over_static(monkeypatch, tmp_path):
    monkeypatch.setattr(am, "PROJECT_ROOT", tmp_path)
    # SLUG is normally in static PRODUCTS, but dynamic catalog should take precedence if set
    custom_product = [
        {
            "title": "Custom Overridden Laptop",
            "subtitle": "Custom override description",
            "search_query": "Custom Laptop Search",
            "badge": "CUSTOM PICK",
            "after_heading": "Acer Aspire 5",
            "specs": ["Custom spec"],
        }
    ]
    am.save_custom_products(SLUG, custom_product)
    prods = am.get_products_for_slug(SLUG)
    assert len(prods) == 1
    assert prods[0]["title"] == "Custom Overridden Laptop"


def test_apply_affiliate_content_with_dynamic_products(monkeypatch, tmp_path):
    monkeypatch.setattr(am, "PROJECT_ROOT", tmp_path)
    custom_slug = "smart-home-devices-2026"
    products = [
        {
            "title": "Echo Dot 5th Gen Smart Speaker",
            "subtitle": "Vibrant sound and Alexa voice control for any room.",
            "search_query": "Echo Dot 5th Gen",
            "badge": "BEST SMART SPEAKER",
            "after_heading": "1. Echo Dot",
            "specs": ["Alexa built-in", "Clear vocals", "Motion detection"],
        },
        {
            "title": "Kasa Smart Plug Mini",
            "subtitle": "Reliable Wi-Fi smart outlet with energy monitoring.",
            "search_query": "Kasa Smart Plug Mini",
            "badge": "BEST BUDGET PLUG",
            "after_heading": "2. Kasa Smart Plug",
            "specs": ["No hub required", "Voice control", "Timer scheduling"],
        },
    ]
    am.save_custom_products(custom_slug, products)

    post_content = """<p>Smart home intro.</p>
<h2>1. Echo Dot (5th Gen)</h2>
<p>Alexa review.</p>
<h2>2. Kasa Smart Plug</h2>
<p>Kasa plug review.</p>
<h2>Conclusion</h2>
<p>Final verdict.</p>
"""
    out, warnings = am.apply_affiliate_content(post_content, custom_slug, TAG, include_quick_picks=True)
    assert warnings == []
    assert 'class="tech-quick-picks"' in out
    assert 'Echo Dot 5th Gen' in out
    assert 'Kasa Smart Plug Mini' in out
    assert f"tag={TAG}" in out
    assert out.count('tech-affiliate-card') == 2

