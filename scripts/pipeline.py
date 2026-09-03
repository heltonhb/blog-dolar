#!/usr/bin/env python3
"""
Blog em Dolar - Orquestrador Principal
Fluxo completo: gerar topicos -> gerar artigos -> publicar
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Adiciona scripts ao path
sys.path.insert(0, str(Path(__file__).parent))

from gerar_artigos import BlogGenerator, save_article
from publicar_wp import WordPressPublisher
from image_generator import generate_article_image, extract_slug_from_filename


def load_config() -> dict:
    """Carrega configuração do .env e do config.yaml (se existir).

    Prioridade: variáveis de ambiente > config.yaml > defaults.
    O parser YAML suporta valores com ':' (ex: URLs).
    """
    config: dict = {}

    # Tenta ler config.yaml se existir
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if ':' in line:
                    key, _, val = line.partition(':')
                    config[key.strip()] = val.strip().strip('"\'')

    # Variáveis de ambiente sobrescrevem o YAML
    env_map = {
        'gemini_api_key': 'GEMINI_API_KEY',
        'wordpress_url': 'SITE_URL',
        'wordpress_username': 'WP_USER',
        'wordpress_app_password': 'WP_APP_PASSWORD',
        'blog_niche': None,
        'blog_posts_per_day': None,
    }
    for yaml_key, env_key in env_map.items():
        if env_key and os.environ.get(env_key):
            config[yaml_key] = os.environ[env_key]

    # Carrega .env se ainda não estiver no ambiente
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                k = k.strip()
                v = v.strip()
                os.environ.setdefault(k, v)
                # Preenche config com as chaves mapeadas
                for yaml_key, env_key in env_map.items():
                    if env_key == k and yaml_key not in config:
                        config[yaml_key] = v

    # Defaults
    config.setdefault('blog_niche', 'technology')
    config.setdefault('blog_posts_per_day', '2')

    return config


def run_full_pipeline():
    """Executa o pipeline completo"""
    
    print("=" * 60)
    print("  BLOG EM DOLAR - Pipeline Completo")
    print("=" * 60)
    print(f"  Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    # 1. Carrega config
    print("\n[1/4] Carregando configuracao...")
    config = load_config()
    
    api_key = config.get('gemini_api_key', '')
    if not api_key:
        api_key = os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        api_key = input("  Cole sua GEMINI_API_KEY: ").strip()
    
    niche = config.get('blog_niche', 'travel')
    posts_per_day = int(config.get('blog_posts_per_day', '2'))
    
    print(f"  Nicho: {niche}")
    print(f"  Artigos/dia: {posts_per_day}")
    
    # 2. Inicia gerador
    print("\n[2/4] Inicializando gerador de conteudo...")
    gen = BlogGenerator(api_key)
    articles_dir = Path(__file__).parent.parent / "articles"
    articles_dir.mkdir(exist_ok=True)
    
    # 3. Gera topicos
    print("\n[3/4] Gerando topicos evergreen...")
    topics = gen.generate_topics(niche, count=posts_per_day + 2)
    
    if not isinstance(topics, list) or len(topics) == 0:
        print("  Erro ao gerar topicos!")
        return
    
    print(f"  {len(topics)} topicos gerados:")
    for i, t in enumerate(topics, 1):
        print(f"    {i}. {t.get('title', 'Sem titulo')}")
    
    # Salva topicos
    topics_file = articles_dir / f"topics_{datetime.now().strftime('%Y%m%d')}.json"
    topics_file.write_text(json.dumps(topics, indent=2, ensure_ascii=False))
    
    # 4. Gera artigos
    print(f"\n[4/4] Gerando {min(posts_per_day, len(topics))} artigo(s)...")
    articles_saved = []
    
    for i, topic in enumerate(topics[:posts_per_day], 1):
        print(f"\n  [{i}/{posts_per_day}] {topic.get('title', '')[:50]}...")
        
        try:
            article = gen.generate_article(topic, topic.get('keyword', niche))
            filepath = save_article(article, articles_dir)
            articles_saved.append(filepath)
            print(f"    OK! ({len(article.get('content', ''))} chars)")
        except Exception as e:
            print(f"    Erro: {e}")
    
    # 5. Gera imagens para artigos
    print(f"\n[5/5] Gerando imagens para {len(articles_saved)} artigo(s)...")
    images_dir = Path(__file__).parent.parent / "images" / "generated"
    images_dir.mkdir(parents=True, exist_ok=True)

    for i, filepath in enumerate(articles_saved, 1):
        try:
            content = filepath.read_text(encoding="utf-8")
            title = filepath.stem.replace("-", " ").title()
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    for line in parts[1].strip().split("\n"):
                        if line.strip().startswith("title:"):
                            title = line.split(":", 1)[1].strip()

            slug = extract_slug_from_filename(filepath.name)

            # Generate Pinterest pin image
            print(f"  [{i}] Pin para: {title[:50]}...")
            img_bytes, provider, prompt = generate_article_image(
                api_key=api_key,
                article_title=title,
                usage="pinterest",
            )
            pin_path = images_dir / f"pin-{slug}.png"
            pin_path.write_bytes(img_bytes)
            print(f"    OK Pin: {pin_path.name} ({len(img_bytes) // 1024}KB via {provider})")

            # Generate featured image
            print(f"  [{i}] Featured para: {title[:50]}...")
            feat_bytes, provider2, _ = generate_article_image(
                api_key=api_key,
                article_title=title,
                usage="featured",
            )
            feat_path = images_dir / f"featured-{slug}.png"
            feat_path.write_bytes(feat_bytes)
            print(f"    OK Featured: {feat_path.name} ({len(feat_bytes) // 1024}KB via {provider2})")

        except Exception as e:
            print(f"    Erro ao gerar imagem: {e}")

    # Resumo
    print("\n" + "=" * 60)
    print("  PIPELINE CONCLUIDO!")
    print("=" * 60)
    print(f"\n  Artigos gerados: {len(articles_saved)}")
    print(f"  Imagens em: {images_dir}")
    print(f"  Local: {articles_dir}")
    
    if articles_saved:
        print("\n  Proximos passos:")
        print("    1. Revise os artigos em articles/")
        print("    2. Rode: python scripts/publicar_wp.py")
        print("    3. Publique como draft e revise no WP")
        print("    4. Mude status para 'publish'")
    
    return articles_saved


def run_scheduler():
    """Modo agendador - roda a cada X horas"""
    import time
    
    print("=" * 60)
    print("  BLOG EM DOLAR - Modo Agendador")
    print("=" * 60)
    
    config = load_config()
    interval_hours = int(config.get('blog_posts_per_day', '2'))
    
    print(f"\n  Gerando {interval_hours} artigos por dia")
    print("  Pressione Ctrl+C para parar\n")
    
    while True:
        try:
            run_full_pipeline()
            
            # Calcula proxima execucao
            next_run = datetime.now().replace(
                hour=datetime.now().hour + (24 // interval_hours)
            )
            print(f"\n  Proxima execucao: {next_run.strftime('%H:%M')}")
            print("  Aguardando... (Ctrl+C para sair)\n")
            
            time.sleep(3600 * (24 // interval_hours))
            
        except KeyboardInterrupt:
            print("\n  Agendador parado.")
            break


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Blog em Dolar - Pipeline")
    parser.add_argument("--schedule", action="store_true", help="Modo agendador")
    parser.add_argument("--once", action="store_true", help="Executa uma vez")
    
    args = parser.parse_args()
    
    if args.schedule:
        run_scheduler()
    else:
        run_full_pipeline()
