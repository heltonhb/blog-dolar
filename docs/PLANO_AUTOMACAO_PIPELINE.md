# Plano de Automação do Pipeline de Conteúdo & Monetização Amazon

> **Status:** Documento criado em 08/10/2026 para orientar a próxima fase de desenvolvimento do Blog em Dólar (`techtips.dpdns.org`).
> **Tag Amazon Associates Ativa:** `heltonhb-20` (Amazon US).

---

## 1. Contexto e Onde Paramos

As 4 etapas fundamentais da estratégia de monetização já estão concluídas e sincronizadas ao vivo no WordPress:
1. **Safe Bridge em Inglês:** Página ponte traduzida (`<html lang="en">`, disclaimers, badges e CTAs).
2. **Motor Multi-Pin:** Gerador de 3 variações visuais por artigo (2:3 vertical, 768×1152) com text overlay e SEO.
3. **Quick Recommendations Box:** Tabela de recomendações rápidas inserida automaticamente acima da dobra (logo após a introdução) com botões diretos para a Amazon, CSS responsivo entregue via mu-plugin e rastreamento de cliques no GA4.
4. **Pauta Buyer Intent & Primeiro Post Publicado:**
   - Post ID **129** publicado no ar: `https://techtips.dpdns.org/2026/10/08/top-5-amazon-tech-gadgets-under-30/`.
   - 7 artigos ao vivo 100% monetizados e auditados via `affiliate_manager.py --check-wp`.
   - Todos os 16 posts interligados via `internal_links.py`.

---

## 2. As 5 Automações Planejadas para o App

O objetivo agora é transformar tarefas manuais de terminal em fluxos integrados e automatizados diretamente pelo Dashboard Flask (`http://localhost:5000`).

---

### 🚀 Automação 1: Extração e Mapeamento Dinâmico de Produtos via IA
* **Problema atual:** Para cada novo artigo sobre um tema inédito, é preciso abrir `scripts/affiliate_manager.py` e editar manualmente o dicionário `PRODUCTS`.
* **Solução:**
  1. No prompt de geração de artigos comerciais (`/generate` e `gerar_artigos.py`), instruir o Gemini a retornar tanto o markdown do artigo quanto um bloco estruturado JSON com os **3 a 5 produtos reais recomendados da Amazon US**:
     ```json
     {
       "products": [
         {
           "title": "Anker Nano 30W USB-C GaN Charger",
           "subtitle": "Compact GaN charger for fast charging phones and laptops.",
           "search_query": "Anker Nano 30W USB-C GaN Charger",
           "badge": "BEST FAST CHARGER",
           "after_heading": "Anker Nano 30W",
           "specs": ["30W GaN output", "Foldable prongs", "Ultra compact"]
         }
       ]
     }
     ```
  2. O backend armazena esses produtos em `dashboard/data/products_catalog.json` (ou tabela SQLite/MySQL) e o `affiliate_manager.py` lê desse catálogo dinâmico além do dicionário estático.
  3. **Impacto:** Zero necessidade de editar código Python para cadastrar produtos.

---

### ⚡ Automação 2: Injeção de Monetização Automática ao Salvar/Publicar
* **Problema atual:** É necessário rodar `python3 scripts/affiliate_manager.py --inject arquivo.md` no terminal antes de publicar.
* **Solução:**
  1. No serviço `dashboard/services/wordpress.py` (função `_wp_publish`), conectar diretamente a chamada a `apply_affiliate_content()` com `include_quick_picks=True`.
  2. Ao clicar no botão **"Publicar no WordPress"** na interface web (`/publish`):
     - O sistema verifica se o artigo já possui `tech-affiliate-card` e `tech-quick-picks`.
     - Caso não tenha, aplica automaticamente o disclosure, a caixa de Quick Recommendations no topo e os cartões de seção com tag `heltonhb-20`.
     - Envia o artigo já monetizado para a REST API do WordPress.
  3. **Impacto:** Impossível publicar um artigo no WordPress sem monetização ou sem a tabela acima da dobra.

---

### 📌 Automação 3: Geração de Pins em Segundo Plano Pós-Publicação
* **Problema atual:** Após publicar, precisa-se rodar `python3 scripts/generate_pin_variations.py --slug ...`.
* **Solução:**
  1. Criar um hook de pós-publicação assíncrono (usando `threading.Thread` ou worker de background):
     - Quando `_wp_publish` retornar `success=True`, dispara `generate_pins_for_slug(slug)`.
  2. O motor gera as 3 variações de Pins (2:3 vertical com text overlays) via Pollinations/Gemini.
  3. As imagens geradas e os textos SEO prontos ficam visíveis e organizados na tela do Dashboard em `/pinterest`.
  4. **Impacto:** Artigo publicado = 3 Pins prontos automaticamente para envio.

---

### 🔗 Automação 4: Interlinking Cruzado Automático
* **Problema atual:** É preciso rodar `internal_links.py --apply` manualmente no terminal.
* **Solução:**
  1. Incorporar a rotina de interlinking após a publicação de um novo artigo.
  2. A rotina calcula os artigos mais similares e faz o PUT no WordPress com o intervalo de 2 segundos entre posts (para evitar o rate limit do InfinityFree que identificamos e tratamos).
  3. **Impacto:** O blog mantém uma malha interna de SEO sempre perfeita e atualizada sem intervenção manual.

---

### 🤖 Automação 5: Pipeline End-to-End de 1-Clique no Scheduler
* **Objetivo:** Criar um botão "Publicar 1 Artigo Comercial Agora" ou ativar no Agendador (`/scheduler`):
  1. Pega 1 ideia pendente da fila de **Buyer Intent** gerada no `/ideas`.
  2. Aciona o Gemini para escrever o artigo e extrair os produtos reais da Amazon.
  3. Salva o markdown local em `articles/`.
  4. Injeta a monetização completa (Quick Picks + cartões de seção + disclosure).
  5. Publica no WordPress (gera a URL viva).
  6. Roda o interlinking cruzado nos posts do blog.
  7. Gera os 3 Pins verticais para o Pinterest.
  8. Emite notificação no painel com o link do post e as 3 imagens prontas.

---

## 3. Roteiro Prático de Retomada (Passo a Passo)

Quando formos implementar essas automações:

### Fase 1: Backend de Produtos Dinâmicos & Auto-Inject (Automações 1 e 2)
1. Modificar [`scripts/gerar_artigos.py`](file:///home/helton/blog-dolar/scripts/gerar_artigos.py) e o endpoint `/api/generate` para solicitar a lista `products` no mesmo JSON da geração de texto.
2. Criar função `save_custom_products(slug, products_list)` no [`scripts/affiliate_manager.py`](file:///home/helton/blog-dolar/scripts/affiliate_manager.py).
3. Integrar no `_wp_publish` em [`dashboard/services/wordpress.py`](file:///home/helton/blog-dolar/dashboard/services/wordpress.py) a chamada obrigatória do `apply_affiliate_content`.
4. Criar testes unitários em `tests/test_affiliate_manager.py` e `tests/test_publish.py`.

### Fase 2: Hooks de Background (Automações 3 e 4)
1. Criar `dashboard/services/post_hooks.py` contendo:
   - `trigger_post_publish_tasks(slug, post_id)` executado em background thread.
   - Tarefa 1: `generate_pins_for_slug(slug)`
   - Tarefa 2: `recalc_internal_links(slug)`
2. Exibir status de progresso das tarefas no Dashboard.

### Fase 3: Piloto Automático no Scheduler (Automação 5)
1. Integrar o workflow de 1-clique em [`dashboard/routes/scheduler.py`](file:///home/helton/blog-dolar/dashboard/routes/scheduler.py).
2. Adicionar botão "Executar Ciclo Completo de Monetização" no dashboard.

---

## 4. Arquivos Envolvidos e Referências

- [`scripts/affiliate_manager.py`](file:///home/helton/blog-dolar/scripts/affiliate_manager.py): Gestor de cartões, Quick Picks e tags.
- [`scripts/generate_pin_variations.py`](file:///home/helton/blog-dolar/scripts/generate_pin_variations.py): Motor multi-pin vertical.
- [`scripts/internal_links.py`](file:///home/helton/blog-dolar/scripts/internal_links.py): Motor de interlinking com delay anti-rate limit.
- [`dashboard/services/wordpress.py`](file:///home/helton/blog-dolar/dashboard/services/wordpress.py): Publicação via REST com bypass de anti-bot.
- [`dashboard/routes/ideas.py`](file:///home/helton/blog-dolar/dashboard/routes/ideas.py): Gerador de ideias com filtro de Buyer Intent.
- [`dashboard/templates/ideas.html`](file:///home/helton/blog-dolar/dashboard/templates/ideas.html): Interface com botão de Buyer Intent.
- [`docs/PLANO_ACAO_AMAZON_2026.md`](file:///home/helton/blog-dolar/docs/PLANO_ACAO_AMAZON_2026.md): Diagnóstico e estratégia de comissões em dólar.
