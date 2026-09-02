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
from publicar_wp import WordPressPublisher, load_config


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
    
    # Resumo
    print("\n" + "=" * 60)
    print("  PIPELINE CONCLUIDO!")
    print("=" * 60)
    print(f"\n  Artigos gerados: {len(articles_saved)}")
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
