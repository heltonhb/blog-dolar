#!/usr/bin/env python3
"""
Blog em Dolar - Gerador de Artigos com IA
Usa Google Gemini API (free tier) para gerar conteudo evergreen
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Instalando httpx...")
    os.system(f"{sys.executable} -m pip install httpx -q")
    import httpx


class BlogGenerator:
    def __init__(self, api_key: str, model: str = "gemini-3.5-flash-lite"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    def generate_topics(self, niche: str, count: int = 10) -> list:
        """Gera topicos evergreen para o niche"""
        prompt = f"""Generate {count} evergreen blog post ideas for a {niche} blog.
        
Focus on topics that will stay relevant for years. Include long-tail keywords.

Return ONLY a JSON array with this format:
[
  {{
    "title": "Article title with main keyword",
    "keyword": "primary long-tail keyword",
    "outline": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"]
  }}
]

No markdown, just pure JSON."""

        response = self._call_api(prompt)
        return self._parse_json(response)
    
    def generate_article(self, topic: dict, keyword: str) -> dict:
        """Gera artigo completo otimizado para SEO"""
        prompt = f"""Write a comprehensive blog post about: {topic['title']}

Target keyword: {keyword}
Outline to follow: {json.dumps(topic.get('outline', []))}

Requirements:
- 1500-2000 words
- Use keyword naturally 5-8 times
- Include H2 and H3 subheadings
- Add comparison table where relevant
- Use bullet points for readability
- Conversational, engaging tone
- Include a meta description (150 chars)

Return ONLY JSON:
{{
  "title": "SEO title",
  "slug": "url-friendly-slug",
  "meta_description": "...",
  "content": "Full HTML article with <h2>, <h3>, <p>, <ul>, <table> tags",
  "tags": ["tag1", "tag2", "tag3"]
}}"""

        response = self._call_api(prompt)
        return self._parse_json(response)
    
    def _call_api(self, prompt: str) -> str:
        """Chama a API do Gemini"""
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192
            }
        }
        
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        
        return data["candidates"][0]["content"]["parts"][0]["text"]
    
    def _parse_json(self, text: str) -> dict | list:
        """Extrai JSON de texto"""
        # Remove markdown code blocks
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        
        # Tenta parsear
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Tenta encontrar JSON no texto
            import re
            match = re.search(r'\[[\s\S]*\]|\{[\s\S]*\}', text)
            if match:
                return json.loads(match.group())
            raise


def save_article(article: dict, output_dir: Path):
    """Salva artigo em arquivo markdown"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}_{article.get('slug', 'untitled')}.md"
    filepath = output_dir / filename
    
    content = f"""---
title: {article.get('title', 'Untitled')}
date: {date_str}
slug: {article.get('slug', '')}
meta_description: {article.get('meta_description', '')}
tags: {json.dumps(article.get('tags', []))}
---

{article.get('content', 'No content')}
"""
    
    filepath.write_text(content, encoding="utf-8")
    print(f"  Artigo salvo: {filepath}")
    return filepath


if __name__ == "__main__":
    print("=" * 50)
    print("  BLOG EM DOLAR - Gerador de Conteudo")
    print("=" * 50)
    
    # Config
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        api_key = input("\nCole sua GEMINI_API_KEY: ").strip()
    
    niche = input("Nicho (travel/finance/tech/food): ").strip() or "travel"
    count = int(input("Quantos topicos gerar (5-10): ").strip() or "5")
    
    gen = BlogGenerator(api_key)
    output_dir = Path(__file__).parent.parent / "articles"
    output_dir.mkdir(exist_ok=True)
    
    # Gerar topicos
    print(f"\nGerando {count} topicos para nicho '{niche}'...")
    topics = gen.generate_topics(niche, count)
    
    if isinstance(topics, list):
        print(f"\nTopicos gerados:")
        for i, t in enumerate(topics, 1):
            print(f"  {i}. {t.get('title', 'Sem titulo')}")
        
        # Salvar topicos
        topics_file = output_dir / f"topics_{datetime.now().strftime('%Y%m%d')}.json"
        topics_file.write_text(json.dumps(topics, indent=2, ensure_ascii=False))
        print(f"\nTopicos salvos em: {topics_file}")
        
        # Gerar artigos
        gerar = input("\nGerar artigos agora? (s/n): ").strip().lower()
        if gerar == "s":
            for i, topic in enumerate(topics[:3], 1):  # Max 3 por vez
                print(f"\n[{i}/{min(3, len(topics))}] Gerando: {topic.get('title', '')}")
                article = gen.generate_article(topic, topic.get('keyword', niche))
                save_article(article, output_dir)
            
            print("\nPronto! Artigos gerados em:", output_dir)
    else:
        print("Erro ao gerar topicos. Resposta:", topics)
