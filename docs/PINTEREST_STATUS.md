# Pinterest Automation — Status (atualizado 2026-09-15, após fixes)

## Conclusão: CÓDIGO 100% PRONTO e corrigido; bloqueado apenas na API (trial pendente)

### Estado real dos recursos
- Token `PINTEREST_ACCESS_TOKEN` no `.env` (`pina_AMA...`) -> **EXPIROU** (401 no teste).
- `PINTEREST_REFRESH_TOKEN`, `CLIENT_ID`, `CLIENT_SECRET` -> **ausentes** no `.env`.
- `PINTEREST_BOARD_ID` -> **vazio** (`.env` e `dashboard/data/pinterest_config.json`).
- `published_pins` / `pinterest_published.json` -> **vazio**.
- Trial do app (ID 1607290): **PENDENTE** — confirmado no painel em 2026-09-15.

### ✔️ Correções aplicadas em 2026-09-15 (aprovadas pelo usuário)
1. **URL da imagem -> URL direta do arquivo.** `get_pin_image_url()` no `pinterest_publish.py`
   agora busca `source_url` na API do WP (via /media/N) em vez de retornar o endpoint REST.
   Com `client` reutilizável para não abrir conexão por post. Fallback Pollinations mantido.
2. **Refresh automático de token.** Adicionado `refresh_access_token()` + `auth_headers()`
   no `pinterest_publish.py`. Em 401/403 renova 1x sozinho (requer CLIENT_ID/SECRET/REFRESH
   no .env) — aplicado no teste de conexão do `main()` e dentro de `create_pin()`.
3. **Indentação do loop de pins corrigida na pipeline (`dashboard/app.py` ~linha 907).**
   O bloco `if resp_pin.status_code` agora está DENTRO do `for pf in pin_files`. Efeitos:
   - Acumula todos os `pin_ids` e grava checkpoint por pin.
   - `resp_pin` nunca fica indefinido (sem NameError com pin_files vazio).
   - Suporta "Bearer " já prefixado no header (evita "Bearer Bearer").
   - Trata 401/403 com mensagem clara + break.
4. **Dedup unificado.** `load_published_pins()`/`save_published_pin()` no `publish.py`
   agora espelham AMBAS as fontes: `pinterest_published.json` (CLI) e
   `pinterest_config.json["published_pins"]` (pipeline/UI). Dedup por article_url/link.
5. **Retry em rate limit (HTTP 429).** 1 retry com 30s de espera no `publish.py`.

### Falta para destravar (depende de VOCÊ/trial)
1. Aprovar trial em developers.pinterest.com/apps/ (copiar Client Secret).
2. Gerar token com escopo `pins:write,board_pins:write,boards:read,pins:read`
   (processo em docs/SETUP_PINTEREST.md).
3. Preencher no `.env`: `PINTEREST_ACCESS_TOKEN`, `PINTEREST_REFRESH_TOKEN`,
   `PINTEREST_CLIENT_ID`, `PINTEREST_CLIENT_SECRET`, `PINTEREST_BOARD_ID`.
4. Rodar `python scripts/pinterest_setup.py` para testar + listar boards.

### Comandos de teste atual (tudo valida, bloqueado só no token)
- `./venv/bin/python scripts/pinterest_publish.py --dry-run --last 1`
- `./venv/bin/python scripts/pinterest_publish.py --dry-run --last 1 --board-id X` (mostra refresh path)
- `./venv/bin/python scripts/pinterest_setup.py` (401 até token/refresh)