# Plano de Melhorias — Blog Dolar

## Objetivo
Tornar o app mais robusto, configurável, seguro e observável, mantendo o pipeline 100% gratuito (Gemini + Pollinations + WordPress REST + Pinterest + AdCash).

## Arquitetura de Implementação
Fatiamento vertical: cada tarefa é um pedaço completo que deixa o sistema funcionando.

## Tarefas

### Fase 1 — Fundação
- [x] T1: Remover `_byethost_session`/`_solve_challenge` de `dashboard/app.py` e `scripts/pinterest_publish.py`; usar `httpx.Client` direto com auth Básica do WP
- [ ] T2: Adicionar `services/wp_client.py` com sessão HTTP reutilizável, retry/backoff e health-check
- [ ] T3: Atualizar `requirements.txt` (adicionar `pybreaker`, `tenacity`)

### Fase 2 — Configurabilidade (CONCLUÍDA em 28/09)
- [x] T4: `IMAGE_PROVIDER` no `.env` — `auto` (padrão) | `gemini` | `pollinations` |
  `together` | `huggingface`. O provedor escolhido entra na frente da fila e os
  demais continuam como fallback (`_provider_chain()` em
  `scripts/image_generator.py`). `huggingface` só entra quando há `HF_TOKEN`
  (o endpoint anônimo do HF responde 401, verificado).
- [x] T5: cache em `cache/images/` — `scripts/image_cache.py` (lógica, junto do
  gerador, usável pelo CLI) + `dashboard/services/image_cache.py` (fachada).
  Chave = SHA-256 de `usage + provider + prompt`; TTL `IMAGE_CACHE_TTL_DAYS`
  (7 dias) via mtime; expirados apagados na leitura + varredura automática
  horária; escrita atômica. Endpoints: `GET/DELETE /api/images/cache`
  (estatísticas e limpeza, `?expired=1` só os vencidos).
  Verificado ao vivo: 1ª geração 35s (Gemini 429 → fallback Pollinations),
  2ª chamada 0,01s do cache com bytes idênticos.

### Fase 3 — Segurança (CONCLUÍDA em 28/09)
- [x] T6: CSRF em todas as requisições mutantes — `dashboard/services/security.py`
  (`install_csrf`): context processor `csrf_token` + `before_request` que aceita
  campo de form ou header `X-CSRF-Token`; `layout.html` faz patch no `fetch()`
  global, então as ~25 chamadas JS existentes passam a enviar o token sem
  alteração individual.
- [x] T7: Rate limiting do `/login` — `dashboard/services/login_throttle.py`
  (5 falhas / 15 min por IP → HTTP 429; sucesso limpa o contador). O
  flask-limiter continua com o orçamento geral por IP.
- [x] T8: `FLASK_SECRET_KEY` sem fallback determinístico —
  `get_secret_key()` usa a env var e, se ausente, gera e persiste chave
  aleatória em `dashboard/data/flask_secret_key` (chmod 600). As duas
  entrypoints (`dashboard/__init__.py` e `dashboard/app.py`) usam a mesma fonte.
- Correção associada: `dashboard/services/helpers.py` usava `sys.path` sem
  `import sys` → `_scripts_dir()` estourava `NameError` nas rotas
  `/api/traffic/ga4|bing/refresh` e `/api/run_script` do entrypoint factory.

### Fase 3.1 — Hardening bloqueadores (CONCLUÍDA em 01/10)
Auditoria crítica encontrou quatro bloqueadores de produção. Todos corrigidos
com teste de regressão em `tests/test_hardening.py` (17 testes).
- [x] T13: `/api/run_script` deixou de ser execução remota de código. Antes
  aceitava qualquer caminho sob `scripts/` **e argv livre**, com o `.env` inteiro
  injetado no processo — uma requisição autenticada = RCE total. Agora há
  allowlist `ALLOWED_SCRIPTS` em `dashboard/routes/settings.py`, validação de
  nome de arquivo (sem `/`, `\`, `..`, sem caminho absoluto), `resolve()` +
  `is_relative_to()` e **zero argumentos vindos da requisição**.
  `GET /api/run_script/allowed` lista o permitido. A cópia em `dashboard/app.py`
  foi removida; a rota passa a ser servida só pelo blueprint.
- [x] T14: `login_required` passou a **falhar fechado**. Sem
  `DASHBOARD_PASSWORD` não existe autenticação possível, então todas as rotas
  protegidas respondem 503 + `logger.error` (antes: "open mode", expondo o
  dashboard inteiro num deploy com env var faltando). `/login` também explica a
  causa em vez de dizer "senha incorreta".
- [x] T15: TLS sempre verificado — removidos todos os `verify=False`
  (`services/wordpress.py`, `routes/adsense.py`, `app.py` e 6 scripts). O
  cliente do WordPress envia Basic auth e o Pinterest envia bearer token.
  `test_no_verify_false_in_source` é o guard estático contra regressão.
- [x] T16: `ProxyFix(x_for=1, x_proto=1, x_host=1)` + cookies
  `HttpOnly`/`SameSite=Lax`/`Secure` (12h) + headers `nosniff`, `DENY`,
  `Referrer-Policy`, CSP e HSTS. `client_ip()` do throttle passou a usar o
  `remote_addr` já corrigido pelo ProxyFix — ler `X-Forwarded-For` cru permitia
  trocar de identidade a cada tentativa e burlar o limite de login.
  Login passou a comparar a senha com `hmac.compare_digest`.

### Fase 3.2 — Eliminar a duplicação (CONCLUÍDA em 02/10)
- [x] T17: `dashboard/app.py` (2.608 linhas) **removido**. Ele duplicava todas
  as rotas dos blueprints como código morto — duas implementações do mesmo
  sistema divergiam, e correções acabavam indo para a cópia que ninguém
  executava (foi assim que bugs "sumiram" e reapareceram). Antes de remover, os
  4 importadores foram repontados para `dashboard.services.*`:
  `scripts/index_search_console.py`, `scripts/pinterest_publish.py`,
  `test_upload.py` e `tests/smoke_bing_dashboard.py` (esse último passou a usar
  `create_app()`). Entrypoints atualizados: `start-dashboard.sh` e o novo
  `dashboard/__main__.py` (`python -m dashboard`; `python -m pkg` executa
  `__main__.py`, não `__init__.py`). `README.md` e `MIGRATION_STATUS.md`
  atualizados. 3 testes de guarda impedem o retorno do monólito.
- [x] T18: suíte isolada da produção. `create_app()` abria conexão com o Neon de
  produção em cada fixture e `POST /api/settings` escrevia no `.env` real (uma
  chave de teste ficou persistida lá). Agora `tests/conftest.py` monta uma
  árvore descartável (`.pytest_sandbox/`, ignorada no git) e define
  `BLOG_DOLAR_ROOT`; `create_app()` respeita `SKIP_DB_INIT`/`SKIP_SCHEDULER`.
  Efeito colateral: **225s → 63s** (3,5× mais rápido) e nenhum teste escreve
  mais no repositório ou no banco.

### Fase 4 — Automação
- [ ] T9: Adicionar `PINTEREST_REFRESH_TOKEN` e endpoint `/api/pinterest/refresh`
- [ ] T10: Atualizar `scripts/pinterest_publish.py` para usar refresh automático em 401/403

### Fase 5 — Testes e Documentação
- [~] T11: `tests/test_security.py` (CSRF, throttle, secret key) e
  `tests/test_image_cache.py` (cache TTL, ordenação de provider, endpoints) —
  falta `tests/test_wp_client.py` (depende de T2)
- [ ] T12: Atualizar `README.md` com novas variáveis e `docs/troubleshooting.md`

## Verificação
- `pytest tests/ -v` passando
- `python dashboard/__init__.py` sem erros de importação
- `docker-compose up --build` sem falhas