# Estratégias para Aumentar o Alcance do Blog em Dolar
# Data: 2026-09-01

## 📊 ESTATÍSTICAS ATUAIS
- Artigos publicados: 6
- Nicho: Tecnologia (CPM $8-20)
- Monetização: AdCash (ativa)

## 🎯 ESTRATÉGIAS DE CRESCIMENTO

### 1. SEO ON-PAGE (Imediato)
- [x] Títulos otimizados com keyword
- [x] Meta descriptions
- [x] URLs amigáveis (slugs)
- [ ] Adicionar imagens aos artigos
- [ ] Intern linking entre artigos
- [ ] Schema markup (FAQ, How-To)

### 2. CONTEÚDO (Semanal)
- [ ] Publicar 2-3 artigos por dia
- [ ] Criar artigos "pillar" (guia completo)
- [ ] Artigos de comparação (vs)
- [ ] Tutoriais passo a passo
- [ ] Listas ("Top 10", "Best of")

### 3. REDES SOCIAIS (Gratuito)
- [ ] Criar conta no Pinterest
- [ ] Criar conta no Twitter/X
- [ ] Criar canal no Telegram
- [ ] Compartilhar em subreddits (r/technology, r/gadgets)
- [ ] Grupos do Facebook (tech)

### 4. DISTRIBUIÇÃO (Automatizado)
- [ ] RSS feed para agregadores
- [ ] Envio para Google News
- [ ] Bing Webmaster Tools
- [ ] Yandex Webmaster

### 5. LINK BUILDING (Médio prazo)
- [ ] Comentar em blogs do nicho
- [ ] Guest posts em sites parceiros
- [ ] Responder perguntas no Quora
- [ ] Criar perfis em diretórios

### 6. MÉTRICAS PARA ACOMPANHAR
- Pageviews/dia
- Tempo no site
- Taxa de rejeição
- Páginas por sessão
- CPM dos anúncios
- Receita diária/mensal

## 📈 METAS

### Mês 1 (Setembro 2026)
- 30 artigos publicados
- 100 pageviews/dia
- Receita: $15-30/mês

### Mês 2 (Outubro 2026)
- 60 artigos publicados
- 500 pageviews/dia
- Receita: $50-100/mês

### Mês 3 (Novembro 2026)
- 90 artigos publicados
- 1000 pageviews/dia
- Receita: $100-200/mês
- Aplicar para Google AdSense

## 🔧 AUTOMAÇÕES CRIADAS

### Distribuição — Dev.to (república com canonical, 24/09/2026)
Anti-bloqueio do problema do Pinterest/ct.ws: o conteúdo vive no Dev.to
(audiência deles) e o SEO consolida no blog via `canonical_url`.

```bash
uv run python scripts/publish_devto.py --list          # 7 candidatos dev (check WP)
uv run python scripts/publish_devto.py <slug> --dry-run # payload sem publicar
uv run python scripts/publish_devto.py <slug>           # publica RASCUNHO (com CTA)
uv run python scripts/publish_devto.py --all            # todos os candidatos
uv run python scripts/publish_devto.py --cta           # aplica CTA nos já publicados
```
- Requer `DEVTO_API_KEY` no .env (dev.to → Settings → Extensions → DEV API Keys)
- CTA de rodapé ("Originally published on Tech Tips") injetado automaticamente
  em todo artigo novo; `--cta` aplica retroativamente nos publicados (idempotente)
- ⚠️ Varnish do dev.to bloqueia UA `Python-urllib` com 403 vazio — o script
  já usa UA custom; se API falhar com 403, é isso
- Suporte anti-bot: `scripts/antibot.py` resolve o challenge AES uma vez
  (cookie vale 6h p/ GET) — base para `fetch_wp_post.py` (REST WP por slug)
  e `fetch_urls.py` (sitemap)

### SEO — Internal linking + Bing (24/09/2026)
- `scripts/internal_links.py`: calcula similaridade Jaccard entre posts
  (título + corpo completo, stopwords removidas) e insere bloco
  "Related Articles" com até 3 links em cada post. Idempotente
  (regenera o bloco sem duplicar). `--dry-run` mostra o plano, `--apply` aplica.
- ⚠️ **Aprendizado crítico**: o anti-bot da InfinityFree valida o User-Agent
  na ESCRITA (POST/PUT) — `Mozilla/5.0` passa, UA customizado recebe o
  challenge AES mesmo com cookie válido. E responde HTTP 200 com HTML do
  challenge, fingindo sucesso. Todos os PUT devem validar o CORPO (JSON?),
  não só o status.
- ⚠️ **IndexNow não funciona no ct.ws**: o anti-bot intercepta até
  `/.well-known/<key>.txt`, então o bot do Bing nunca valida a key (422).
  Para Bing/Yandex: importar o site no Bing Webmaster Tools
  (https://www.bing.com/webmasters → Importar do Google Search Console,
  1 clique) — o Bingbot renderiza JS, como o Google.
- `scripts/limpar_cache.py`: limpa o cache do WP Super Cache via FTP —
  rodar SEMPRE após mudanças no site (senão nada aparece).
- Estado: 10/11 posts com bloco "Related Articles" no ar (verificado
  no HTML público). O 11º (top-essential-tech-tips) ficou sem links por
  similaridade abaixo do limiar 0.06 — correto, link forçado é ruído.


### Dashboard (http://localhost:5000)
- Gerador de ideias com IA
- Gerador de artigos com Gemini API
- Publicador automático
- Verificador de status

### Scripts
- gerar_artigos.py - Gera artigos automaticamente
- publish_auto.py - Publica no WordPress
- verificar_servidor.py - Monitora o site

## 💡 DICAS RÁPIDAS

1. **Frequência**: Publique pelo menos 1 artigo por dia
2. **Qualidade**: Artigos com 1500+ palavras ranqueiam melhor
3. **Keywords**: Use ferramentas gratuitas (Ubersuggest, AnswerThePublic)
4. **Imagens**: Adicione imagens gratuitas (Unsplash, Pexels)
5. **Velocidade**: Otimize imagens para carregamento rápido
6. **Mobile**: 60% do tráfego é mobile - teste sempre

## 🚀 PRÓXIMOS PASSOS IMEDIATOS

1. Criar conta no Pinterest (10 min)
2. Criar conta no Twitter/X (10 min)
3. Gerar 5 novos artigos com IA (15 min)
4. Publicar todos via dashboard (5 min)
5. Compartilhar primeiro artigo nas redes (5 min)

Total: 45 minutos para dobrar o alcance!
