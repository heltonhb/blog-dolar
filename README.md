# Blog em Dolar

Sistema automatizado para criar e monetizar blogs em dólar usando IA 100% gratuita.

Pipeline completo: **Ideia → Artigo (Gemini) → Imagem → WordPress (REST API) → Pinterest**

---

## Início Rápido

```bash
# 1. Ativar ambiente virtual
source venv/bin/activate

# 2. Copiar e preencher credenciais
cp .env.example .env
nano .env

# 3. Instalar dependências (se necessário)
pip install -r requirements.txt

# 4. Iniciar o dashboard
python dashboard/app.py
# Acesse: http://localhost:5001
```

---

## Estrutura do Projeto

```
blog-dolar/
├── dashboard/
│   ├── app.py              # Flask dashboard (11 páginas + APIs)
│   ├── data/               # JSONs de estado (ideias, histórico, adcash)
│   ├── static/images/      # Imagens geradas para pins
│   └── templates/          # HTML (login, scheduler, pipeline, verify...)
├── scripts/
│   ├── gerar_artigos.py    # BlogGenerator — geração de artigos via Gemini
│   ├── publicar_wp.py      # WordPressPublisher — REST API
│   ├── pipeline.py         # Orquestrador CLI
│   └── image_generator.py  # Geração de imagens (Gemini + Pollinations)
├── articles/               # Artigos .md gerados
├── config/
│   └── config.yaml.example # Template de configuração CLI
├── .env.example            # Template de variáveis de ambiente
└── blog.sh                 # CLI dispatcher
```

---

## Configuração

### 1. Variáveis de ambiente (`.env`)

Copie `.env.example` para `.env` e preencha:

| Variável | Onde obter |
|---|---|
| `DASHBOARD_PASSWORD` | Defina você mesmo (protege o dashboard) |
| `GEMINI_API_KEY` | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) — gratuito |
| `SITE_URL` | URL do seu WordPress |
| `WP_USER` | Usuário do WordPress |
| `WP_APP_PASSWORD` | WP Admin → Usuários → Perfil → Senhas de Aplicativo |
| `ADCASH_API_TOKEN` | Painel Publisher AdCash |
| `PINTEREST_ACCESS_TOKEN` | [developers.pinterest.com](https://developers.pinterest.com) |

### 2. Pipeline CLI (opcional)

```bash
cp config/config.yaml.example config/config.yaml
nano config/config.yaml
```

---

## Dashboard

Acesse `http://localhost:5001` após iniciar o `app.py`.

### Páginas disponíveis

| Página | Função |
|---|---|
| `/` | Dashboard — stats, workflow, atividade recente |
| `/ideas` | Gerenciar ideias (IA Gemini ou Google Trends RSS) |
| `/generate` | Gerar artigo avulso por palavra-chave |
| `/articles` | Listar e deletar artigos locais |
| `/images` | Galeria de pins gerados |
| `/verify` | Verificação SEO heurística + revisão Gemini AI |
| `/publish` | Publicar artigo avulso no WordPress (REST API) |
| `/pipeline` | Pipeline completo com checkpoints |
| `/scheduler` | Agendador integrado (APScheduler) |
| `/pinterest` | Gerenciar pins |
| `/adcash` | Stats de receita (API real) |
| `/settings` | Editar `.env` via UI |

---

## Funcionalidades

### Segurança
- **Autenticação** com `DASHBOARD_PASSWORD` no `.env`
- Todas as rotas protegidas por `@login_required`
- Credenciais nunca hardcoded

### Pipeline Automático (`/pipeline`)
1. Gera artigo com Gemini (ou reutiliza existente)
2. Gera imagem Pinterest (3:4) + featured image (16:9) via Gemini Imagen
3. **Faz upload da imagem para a biblioteca de mídia do WordPress** → obtém URL pública real
4. Publica o artigo via **WordPress REST API** (com imagem destacada)
5. Cria pin no Pinterest com a URL pública da imagem WP

**Checkpoints por slug**: se o pipeline falhar após gerar o artigo, na próxima execução ele retoma do passo que parou — sem re-gastar tokens de API.

### Agendador (`/scheduler`)
- Jobs de pipeline em horários fixos sem cron externo
- Persistência em JSON — restaurados automaticamente ao reiniciar
- Botão "Executar agora" para teste

### Geração de Ideias (`/ideas`)
- **IA Gemini**: 10 ideias evergreen
- **Google Trends RSS**: busca tendências reais do dia (EUA) e filtra as de tecnologia com Gemini — sem chave de API

### Verificação SEO (`/verify`)
- **Heurístico**: contagem de palavras, H2/H3, links, imagens, meta description
- **Gemini AI**: análise editorial completa — readability, keyword density, sugestões de melhoria, veredicto SEO

### AdCash (`/adcash`)
- Chamada real à **Publisher API** (`/api/v2/stats`)
- Exibe revenue, impressões, cliques, eCPM por dia

---

## CLI

```bash
./blog.sh gerar          # Gera artigos via Gemini
./blog.sh publicar       # Publica no WordPress via REST API
./blog.sh pipeline       # Pipeline completo (gerar + imagens)
./blog.sh schedule       # Modo agendador (a cada X horas)
```

---

## Ferramentas 100% gratuitas

| Função | Ferramenta | Custo |
|---|---|---|
| Texto IA | Google Gemini Flash Lite | $0 |
| Imagem IA | Gemini Imagen 3 | $0 |
| Imagem fallback | Pollinations.ai | $0 |
| Tendências | Google Trends RSS | $0 |
| CMS | WordPress + ByetHost | $0 |
| Anúncios | AdCash | $0 (rev share) |
| Pinterest | Pinterest API v5 | $0 |
| Agendador | APScheduler (embutido) | $0 |
