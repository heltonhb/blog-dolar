# Plano de Melhorias — Blog Dolar

## Objetivo
Tornar o app mais robusto, configurável, seguro e observável, mantendo o pipeline 100% gratuito (Gemini + Pollinations + WordPress REST + Pinterest + AdCash).

## Arquitetura de Implementação
Fatiamento vertical: cada tarefa é um pedaço completo que deixa o sistema funcionando.

## Tarefas

### Fase 1 — Fundação
- [ ] T1: Remover `_byethost_session`/`_solve_challenge` de `dashboard/app.py` e `scripts/pinterest_publish.py`; usar `httpx.Client` direto com auth Básica do WP
- [ ] T2: Adicionar `services/wp_client.py` com sessão HTTP reutilizável, retry/backoff e health-check
- [ ] T3: Atualizar `requirements.txt` (adicionar `pybreaker`, `tenacity`)

### Fase 2 — Configurabilidade
- [ ] T4: Adicionar `IMAGE_PROVIDER` no `.env` (`gemini`|`pollinations`|`huggingface`) e cache em `cache/images/` com hash do prompt
- [ ] T5: Adicionar `services/image_cache.py` com TTL de 7 dias e limpeza automática

### Fase 3 — Segurança
- [ ] T6: Adicionar `CSRF` token em todos os forms (Flask-WTF ou implementação própria)
- [ ] T7: Aplicar rate limiting explícito em `/login` (5 tentativas / 15 min)
- [ ] T8: Gerar `FLASK_SECRET_KEY` obrigatório se `DASHBOARD_PASSWORD` estiver setado

### Fase 4 — Automação
- [ ] T9: Adicionar `PINTEREST_REFRESH_TOKEN` e endpoint `/api/pinterest/refresh`
- [ ] T10: Atualizar `scripts/pinterest_publish.py` para usar refresh automático em 401/403

### Fase 5 — Testes e Documentação
- [ ] T11: Criar `tests/test_wp_client.py`, `tests/test_image_cache.py`, `tests/test_auth.py`
- [ ] T12: Atualizar `README.md` com novas variáveis e `docs/troubleshooting.md`

## Verificação
- `pytest tests/ -v` passando
- `python dashboard/__init__.py` sem erros de importação
- `docker-compose up --build` sem falhas