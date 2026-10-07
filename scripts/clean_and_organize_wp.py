#!/usr/bin/env python3
"""
Clean and organize WordPress site:
1. Creates well-defined categories (Hardware, Software, AI, Security).
2. Assigns all published posts to their proper categories (removing 'Uncategorized').
3. Fixes post titles with outdated years.
4. Confirms final state.
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.services.wordpress import _antibot_session
from dashboard.services.helpers import _load_env_dict, _env


def main():
    env = _load_env_dict()
    site_url = env.get("SITE_URL") or _env("SITE_URL", "https://techtips.dpdns.org")
    wp_user = env.get("WP_USER") or _env("WP_USER", "")
    wp_pass = env.get("WP_APP_PASSWORD") or _env("WP_APP_PASSWORD", "")
    auth = (wp_user, wp_pass)

    base_api = f"{site_url.rstrip('/')}/wp-json/wp/v2"
    client = _antibot_session(site_url)

    print("=== 1. Verificando/Criando Categorias ===")
    desired_cats = [
        {
            "name": "Hardware & Devices",
            "slug": "hardware-devices",
            "description": "Reviews, comparisons, and guides on computers, storage, and tech accessories."
        },
        {
            "name": "Software & Tutorials",
            "slug": "software-tutorials",
            "description": "Actionable programming guides, web design tips, and software tutorials."
        },
        {
            "name": "AI & Emerging Tech",
            "slug": "ai-emerging-tech",
            "description": "Insights and explanations on artificial intelligence and next-gen technology."
        },
        {
            "name": "Security & Privacy",
            "slug": "security-privacy",
            "description": "Practical advice to safeguard your digital privacy and protect your accounts."
        }
    ]

    cat_map = {}
    r = client.get(f"{base_api}/categories?per_page=100", auth=auth)
    existing_cats = {c["slug"]: c["id"] for c in r.json()} if r.status_code == 200 else {}

    for c in desired_cats:
        slug = c["slug"]
        if slug in existing_cats:
            cat_map[slug] = existing_cats[slug]
            print(f"  [OK] Categoria existente: {c['name']} (ID: {existing_cats[slug]})")
        else:
            resp = client.post(f"{base_api}/categories", auth=auth, json=c)
            if resp.status_code in (200, 201):
                new_id = resp.json()["id"]
                cat_map[slug] = new_id
                print(f"  [+] Categoria criada: {c['name']} (ID: {new_id})")
            else:
                print(f"  [ERRO] Falha ao criar categoria {c['name']}: {resp.text[:200]}")

    print("\n=== 2. Mapeando e Atualizando Posts ===")
    # Slug or ID mapping to categories
    post_category_mapping = {
        107: "hardware-devices",    # SSD vs HDD Storage Difference
        97:  "security-privacy",    # How to Choose a Secure Password Manager
        96:  "ai-emerging-tech",    # How Will AI Affect Future Jobs?
        41:  "ai-emerging-tech",    # History of Artificial Intelligence Explained
        40:  "software-tutorials",  # History and Future of Cloud Computing
        39:  "hardware-devices",    # Best Budget Laptops for Students 2026
        35:  "ai-emerging-tech",    # AI in Healthcare
        30:  "software-tutorials",  # Learn Git Version Control
        29:  "software-tutorials",  # Pick a Programming Language
        26:  "software-tutorials",  # Responsive Web Design Best Practices
        25:  "ai-emerging-tech",    # AI vs Machine Learning
        24:  "ai-emerging-tech",    # Quantum Computing 2026
        13:  "hardware-devices",    # Top 5 Best Portable Power Banks
        10:  "software-tutorials",  # Top Essential Tech Tips for 2026
    }

    # Fetch current posts
    r = client.get(f"{base_api}/posts?per_page=100", auth=auth)
    posts = r.json() if r.status_code == 200 else []

    for p in posts:
        pid = p["id"]
        title = p["title"]["rendered"]
        target_cat_slug = post_category_mapping.get(pid, "software-tutorials")
        target_cat_id = cat_map.get(target_cat_slug)

        payload = {}
        if target_cat_id:
            payload["categories"] = [target_cat_id]

        if pid == 26 and "2024" in title:
            payload["title"] = "Responsive Web Design Best Practices: The Ultimate Guide"
            print(f"  [!] Atualizando título do post 26 para remover '2024'")

        if payload:
            update_r = client.post(f"{base_api}/posts/{pid}", auth=auth, json=payload)
            if update_r.status_code in (200, 201):
                print(f"  [OK] Post {pid} ('{title[:35]}...') -> Categoria: {target_cat_slug}")
            else:
                print(f"  [ERRO] Post {pid} falhou: {update_r.text[:200]}")

    print("\n=== 3. Estado Final dos Posts ===")
    r_check = client.get(f"{base_api}/posts?per_page=100", auth=auth)
    if r_check.status_code == 200:
        for p in r_check.json():
            cats = p.get("categories", [])
            print(f"ID {p['id']} | Cats: {cats} | {p['title']['rendered']}")

    print("\n[CONCLUÍDO] Organização finalizada com sucesso!")


if __name__ == "__main__":
    main()
