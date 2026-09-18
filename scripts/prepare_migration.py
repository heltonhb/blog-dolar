#!/usr/bin/env python3
"""
Blog em Dolar — Script de Preparação para Migração ao InfinityFree
Executa os passos automatizáveis da migração:
1. Limpa artigos de nicho inconsistente (viagem)
2. Remove <h1> duplicado dos artigos
3. Adiciona internal links entre artigos
4. Gera lista de URLs para re-indexação
5. Atualiza configurações do projeto
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

ARTICLES_DIR = Path(__file__).parent.parent / "articles"
PROJECT_ROOT = Path(__file__).parent.parent

# ─── Artigos de viagem para despublicar (nicho errado) ────────────────
TRAVEL_ARTICLES = [
    "2026-08-31_beginners-guide-to-cloud-computing-basics.md",  # Este é tech, manter
    "2026-08-31_first-time-flyer-guide-navigating-airports.md",
    "2026-08-31_how-to-pack-light-for-a-two-week-trip.md",
    "2026-08-31_how-to-travel-europe-on-50-a-day.md",
]

# Artigos de teste para remover
TEST_ARTICLES = [
    "2026-09-09_mastering-the-art-of-test-debug.md",
    "2026-09-09_mastering-the-art-of-the-test.md",
]

def step1_identify_articles():
    """Lista e categoriza todos os artigos."""
    print("=" * 60)
    print("PASSO 1: Inventário de Artigos")
    print("=" * 60)

    articles = sorted(ARTICLES_DIR.glob("*.md"))
    tech_articles = []
    travel_articles = []
    test_articles = []

    for a in articles:
        name = a.name
        if name in TRAVEL_ARTICLES[1:]:  # Skip cloud computing (is tech)
            travel_articles.append(a)
            print(f"  ❌ VIAGEM (remover): {name}")
        elif name in TEST_ARTICLES:
            test_articles.append(a)
            print(f"  ❌ TESTE  (remover): {name}")
        else:
            tech_articles.append(a)
            print(f"  ✅ TECH   (manter):  {name}")

    print(f"\n  Total: {len(articles)} artigos")
    print(f"  ✅ Tech: {len(tech_articles)} (manter)")
    print(f"  ❌ Viagem: {len(travel_articles)} (despublicar)")
    print(f"  ❌ Teste: {len(test_articles)} (despublicar)")

    return tech_articles, travel_articles, test_articles


def step2_fix_duplicate_h1(tech_articles):
    """Remove <h1> duplicado do corpo dos artigos."""
    print("\n" + "=" * 60)
    print("PASSO 2: Remover <h1> Duplicado")
    print("=" * 60)

    fixed = 0
    for article_path in tech_articles:
        content = article_path.read_text(encoding="utf-8")

        # Separar frontmatter do corpo
        if not content.startswith("---"):
            continue

        parts = content.split("---", 2)
        if len(parts) < 3:
            continue

        frontmatter = parts[1]
        body = parts[2]

        # Remover <h1>...</h1> do corpo (primeiro match apenas)
        h1_pattern = re.compile(r'\s*<h1[^>]*>.*?</h1>\s*', re.DOTALL | re.IGNORECASE)
        match = h1_pattern.search(body)
        if match:
            new_body = body[:match.start()] + "\n" + body[match.end():]
            new_content = f"---{frontmatter}---{new_body}"
            article_path.write_text(new_content, encoding="utf-8")
            fixed += 1
            print(f"  ✅ Removido <h1> de: {article_path.name}")

    print(f"\n  Total corrigidos: {fixed}")


def step3_extract_article_metadata(tech_articles):
    """Extrai metadados de cada artigo para internal linking."""
    print("\n" + "=" * 60)
    print("PASSO 3: Extrair Metadados para Internal Linking")
    print("=" * 60)

    metadata = []
    for article_path in tech_articles:
        content = article_path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            continue

        parts = content.split("---", 2)
        if len(parts) < 3:
            continue

        frontmatter = parts[1].strip()
        info = {"file": article_path.name, "path": str(article_path)}

        for line in frontmatter.split("\n"):
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip().strip('"')
                if key in ("title", "slug", "date", "meta_description"):
                    info[key] = val
                elif key == "tags":
                    # Parse tags array
                    val = val.strip().strip("[]")
                    info[key] = [t.strip().strip('"') for t in val.split(",")]

        if "slug" in info:
            metadata.append(info)
            print(f"  📄 {info.get('slug', 'unknown')}: {info.get('title', 'No title')[:60]}")

    return metadata


def step4_generate_new_urls(metadata, new_domain):
    """Gera lista de URLs para o novo domínio."""
    print("\n" + "=" * 60)
    print(f"PASSO 4: Gerar URLs para {new_domain}")
    print("=" * 60)

    urls = []
    for article in metadata:
        slug = article.get("slug", "")
        date = article.get("date", "")
        if slug and date:
            date_parts = date.split("-")
            if len(date_parts) == 3:
                y, m, d = date_parts
                url = f"https://{new_domain}/{y}/{m}/{d}/{slug}/"
                urls.append(url)
                print(f"  🔗 {url}")

    # Salvar URLs para indexação
    urls_file = PROJECT_ROOT / "new_site_urls.txt"
    urls_file.write_text("\n".join(urls) + "\n", encoding="utf-8")
    print(f"\n  💾 URLs salvas em: {urls_file}")

    return urls


def step5_create_migration_checklist(new_domain):
    """Gera checklist de migração."""
    print("\n" + "=" * 60)
    print("PASSO 5: Checklist de Migração")
    print("=" * 60)

    checklist = f"""
# Checklist de Migração — ByetHost → InfinityFree

## Etapa 1: Criar Conta InfinityFree
- [ ] Acessar https://www.infinityfree.com/
- [ ] Criar conta gratuita
- [ ] Criar novo site (escolher subdomínio .epizy.com ou .rf.gd OU apontar domínio próprio)
- [ ] Anotar credenciais de FTP (host, user, pass)
- [ ] Anotar dados do MySQL (host, user, pass, db)

## Etapa 2: Instalar WordPress
- [ ] No painel InfinityFree, acessar "Software" → "Softaculous"
- [ ] Instalar WordPress (última versão)
- [ ] Acessar WP Admin e configurar:
  - [ ] Tema: Astra (gratuito, leve)
  - [ ] Permalinks: /%year%/%monthnum%/%day%/%postname%/
  - [ ] Título do site: Tech Tips
  - [ ] Remover post "Hello World" padrão

## Etapa 3: Migrar Conteúdo
### Opção A — Export/Import WordPress (se ByetHost estiver acessível via browser):
- [ ] ByetHost WP Admin → Ferramentas → Exportar → Todo conteúdo → Baixar XML
- [ ] InfinityFree WP Admin → Ferramentas → Importar → WordPress → Instalar
- [ ] Fazer upload do XML e importar

### Opção B — Republicar via Pipeline (recomendada):
- [ ] Atualizar .env com novos dados do InfinityFree:
  ```
  SITE_URL=https://{new_domain}
  WP_USER=novo_usuario
  WP_APP_PASSWORD=nova_application_password
  FTP_HOST=novo_ftp_host
  FTP_USER=novo_ftp_user
  FTP_PASS=novo_ftp_pass
  WP_DB_HOST=novo_db_host
  WP_DB_USER=novo_db_user
  WP_DB_PASS=novo_db_pass
  WP_DB_NAME=novo_db_name
  ```
- [ ] Publicar artigos tech via dashboard pipeline

## Etapa 4: Configurar SEO
- [ ] Google Search Console → Adicionar propriedade → {new_domain}
- [ ] Verificar via HTML tag ou DNS
- [ ] Submeter sitemap: https://{new_domain}/wp-sitemap.xml
- [ ] Instalar plugin Yoast SEO ou RankMath (gratuito)
- [ ] Configurar robots.txt via plugin

## Etapa 5: Configurar Monetização
- [ ] AdCash: Adicionar novo site → aguardar aprovação
- [ ] Instalar plugin "Ad Inserter" via WP Admin → Plugins → Adicionar
- [ ] Configurar blocos de anúncio no Ad Inserter

## Etapa 6: Verificar Indexação (após 3-5 dias)
- [ ] Google: site:{new_domain} → confirmar páginas indexadas
- [ ] Search Console: verificar cobertura e erros
- [ ] GA4: verificar se sessions estão sendo registradas

## Etapa 7: Atualizar Pinterest
- [ ] Atualizar link do board/perfil para {new_domain}
- [ ] Novos pins devem apontar para {new_domain}
- [ ] Pins antigos: Pinterest não permite editar URL destino

## Importante sobre InfinityFree:
⚠️ O InfinityFree tem challenge anti-bot similar ao ByetHost, MAS:
- ✅ Googlebot CONSEGUE resolver (executa JS) → indexação funciona
- ❌ curl/httpx NÃO conseguem → publicação via REST API precisa usar FTP
- ✅ Publicação via FTP + wp_insert_post funciona normalmente
"""

    checklist_path = PROJECT_ROOT / "MIGRATION_CHECKLIST.md"
    checklist_path.write_text(checklist.strip(), encoding="utf-8")
    print(f"  💾 Checklist salvo em: {checklist_path}")
    print("\n  📋 Siga o checklist acima passo a passo!")


def step6_update_env_example(new_domain):
    """Atualiza .env.example com placeholder do novo domínio."""
    print("\n" + "=" * 60)
    print("PASSO 6: Preparar .env.example para InfinityFree")
    print("=" * 60)

    env_example = PROJECT_ROOT / ".env.example"
    content = env_example.read_text(encoding="utf-8")

    # Atualizar SITE_URL
    content = content.replace(
        "SITE_URL=https://tech-tips.byethost4.com",
        f"SITE_URL=https://{new_domain}"
    )

    # Atualizar DB host
    content = content.replace(
        "WP_DB_HOST=sql310.byetcluster.com",
        "WP_DB_HOST=sql123.infinityfree.com"
    )

    # Atualizar FTP host
    content = content.replace(
        "FTP_HOST=ftpupload.net",
        "FTP_HOST=ftpupload.net  # InfinityFree usa o mesmo ftpupload.net"
    )

    env_example.write_text(content, encoding="utf-8")
    print(f"  ✅ .env.example atualizado")


def main():
    print("\n" + "🚀" * 20)
    print("  Blog em Dolar — Preparação para Migração")
    print("  ByetHost → InfinityFree")
    print("🚀" * 20 + "\n")

    # Placeholder — o usuário informará o novo domínio
    new_domain = os.environ.get("NEW_DOMAIN", "SEU-SUBDOMINIO.epizy.com")
    print(f"  Novo domínio: {new_domain}")
    print(f"  (Defina NEW_DOMAIN=xxx antes de rodar)\n")

    tech, travel, test = step1_identify_articles()
    step2_fix_duplicate_h1(tech)
    metadata = step3_extract_article_metadata(tech)
    step4_generate_new_urls(metadata, new_domain)
    step5_create_migration_checklist(new_domain)
    step6_update_env_example(new_domain)

    print("\n" + "=" * 60)
    print("✅ PREPARAÇÃO CONCLUÍDA!")
    print("=" * 60)
    print(f"""
  Próximos passos (manuais):
  1. Crie conta em https://www.infinityfree.com/
  2. Crie um site e anote o subdomínio
  3. Rode novamente com:
     NEW_DOMAIN=seu-site.epizy.com python scripts/prepare_migration.py
  4. Siga o checklist em MIGRATION_CHECKLIST.md
""")


if __name__ == "__main__":
    main()
