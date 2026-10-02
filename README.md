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
| `IMAGE_PROVIDER` | Opcional: provedor de imagem preferido (`auto`/`gemini`/`pollinations`/`together`/`huggingface`) |
| `IMAGE_CACHE_TTL_DAYS` | Opcional: TTL do cache de imagens (padrão 7) |
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
| `/adsense` | Informações AdSense + verificação da tag/ads.txt no site |
| `/settings` | Editar `.env` via UI |

---

## Funcionalidades

### Segurança
- **Autenticação** com `DASHBOARD_PASSWORD` no `.env`
- Todas as rotas protegidas por `@login_required`
- **Fail-closed**: sem `DASHBOARD_PASSWORD` configurado o dashboard recusa
  todas as rotas protegidas (HTTP 503 + log `ERROR`) em vez de abrir o acesso.
  Sem senha não existe autenticação — não há modo aberto.
- Credenciais nunca hardcoded
- **`/api/run_script` com allowlist**: só executa scripts de manutenção
  declarados em `ALLOWED_SCRIPTS` (`dashboard/routes/settings.py`), apenas pelo
  nome do arquivo (sem `/`, `\`, `..` nem caminho absoluto), com
  `resolve()` + `is_relative_to()` para confirmar que o alvo está dentro de
  `scripts/`, e **sem argumentos vindos da requisição**. Os scripts rodam com
  os próprios defaults.
  - `GET /api/run_script/allowed` lista o que é permitido
- **TLS sempre verificado**: nenhum módulo desliga a validação de certificado
  (`verify=False`). As requisições ao WordPress levam Basic auth e ao Pinterest
  bearer token — romper o TLS significaria credencial em claro.
  Teste estático `test_no_verify_false_in_source` impede a regressão.
- **CSRF** em toda requisição mutante (POST/PUT/PATCH/DELETE): token
  injetado nos templates e enviado automaticamente pelo `fetch()` patchado no
  `layout.html` — API aceita o campo `csrf_token` ou o header `X-CSRF-Token`
- **Rate limit no `/login`**: 5 senhas erradas em 15 min por IP → HTTP 429
  (`dashboard/services/login_throttle.py`); login bem-sucedido zera o contador.
  A identidade vem do `remote_addr` já corrigido pelo `ProxyFix` — ler o
  `X-Forwarded-For` cru permitiria trocar de identidade a cada tentativa.
- **`FLASK_SECRET_KEY`**: usa a variável de ambiente; se ausente, gera chave
  aleatória e a persiste em `dashboard/data/flask_secret_key` (chmod 600) —
  nunca um fallback determinístico, que permitiria forjar cookies de sessão
- **Login em tempo constante** (`hmac.compare_digest`) e rotação do token CSRF
  após autenticação (session fixation).
- **`ProxyFix`** (x_for/x_proto/x_host = 1): atrás do proxy do Render o WSGI vê
  o IP do proxy, o que tornava o rate limit global e quebrava as URLs das
  bridge pages. Confia exatamente um salto.
- **Cookies de sessão**: `HttpOnly`, `SameSite=Lax`, `Secure` (desligue com
  `FORCE_HTTPS=0` só para dev local em http) e validade de 12h.
- **Headers de segurança**: `X-Content-Type-Options`, `X-Frame-Options: DENY`,
  `Referrer-Policy`, CSP (`object-src 'none'`, `base-uri 'self'`,
  `frame-ancestors 'none'`) e HSTS quando servido por https.
- Testes: `tests/test_security.py` cobre CSRF, throttle e secret key;
  `tests/test_hardening.py` cobre a allowlist do runner, o fail-closed, o TLS e
  os headers/cookies.

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

### Imagens (provedor + cache)
- **`IMAGE_PROVIDER`**: ordem de geração — `auto` (padrão: together-flux →
  gemini-imagen → pollinations), ou force `gemini`, `pollinations`, `together`
  ou `huggingface` (exige `HF_TOKEN`). O escolhido vai para frente da fila e os
  demais permanecem como fallback.
- **Cache em `cache/images/`**: chave = SHA-256 de `usage + provider + prompt`;
  TTL `IMAGE_CACHE_TTL_DAYS` (7 dias), expirados apagados automaticamente.
  Reexecutar o pipeline / repetir um prompt não gasta cota de API.
- **API**: `GET /api/images/cache` (arquivos, tamanho, TTL, provider ativo) e
  `DELETE /api/images/cache` (`?expired=1` limpa só os vencidos).

### AdSense (`/adsense`)
- Mostra publisher ID, site declarado e acesso rápido ao painel do AdSense
- **Verificação ao vivo** (`/api/adsense/status`): script `adsbygoogle`, meta `google-adsense-account` e linha do Google no `ads.txt`
- Lista as pendências da conta (mensagem de consentimento CMP para EEA/UK/Suíça)

### AdCash / Adsterra (APIs legadas)
- Endpoints `/api/adcash`, `/api/adsterra` continuam disponíveis, mas as abas de UI foram removidas

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
