# Pinterest — Gerar token com permissão de ESCRITA

Passo a passo para renovar o `PINTEREST_ACCESS_TOKEN` com escopo de escrita
(`pins:write`, `boards:write`), exigido pela publicação automática de pins.

> **Status:** executado com sucesso em 2026-11-02 — token com
> `boards:read boards:write pins:read pins:write user_accounts:read`,
> refresh token salvo, pin publicado: `732116483233096989`.

## Diagnóstico (por que a publicação falha hoje)

Teste executado em 2026-11-02 com as credenciais do `.env`:

| Etapa | Resultado |
|---|---|
| `GET /user_account` | ✅ 200 — conta `hbscaro` |
| `GET /boards`, `GET /pins` | ✅ 200 |
| `POST /pins` | ❌ **401** — `Missing: ['boards:write', 'pins:write']` |

O token atual é **read-only**. Não existe `PINTEREST_REFRESH_TOKEN` no `.env`,
então o refresh automático de `scripts/pinterest_publish.py:186` também falha.

Erro do painel ao usar `https://localhost` como redirect:
> Esse aplicativo não registrou um URI de redirecionamento.

Ou seja: o app **1621913 não tem nenhum redirect URI cadastrado**.

---

## Passo 1 — Registrar o redirect URI

1. Abra https://developers.pinterest.com/apps/1621913/
2. Clique em **Manage** → aba **Configure**
3. Na seção **Redirect URIs**, cole exatamente (com a barra final):
   ```
   http://localhost:8765/
   ```
4. Clique em **Add**

> O valor do `redirect_uri` na URL de autorização precisa ser **idêntico**
> byte a byte ao cadastrado (host, porta e barra final).

## Passo 2 — Subir o capturador do `code` (terminal local)

O listener recebe o `code` do Pinterest e grava em `/tmp/pinterest_code.json`
(override com `PINTEREST_CODE_FILE`):

```bash
./.venv/bin/python scripts/pinterest_oauth_listener.py 8765
```

Deixe rodando em um terminal (ou em background com `nohup ... &`).

## Passo 3 — Autorizar no navegador

Abra a URL e clique em **Autorizar**:

```
https://www.pinterest.com/oauth/?client_id=1621913&response_type=code&redirect_uri=http%3A%2F%2Flocalhost%3A8765%2F&scope=boards%3Aread%2Cboards%3Awrite%2Cpins%3Aread%2Cpins%3Awrite%2Cboard_pins%3Awrite%2Cuser_accounts%3Aread
```

O navegador redireciona para `http://localhost:8765/?code=...` e mostra
**"Code recebido!"**.

Escopos pedidos: `boards:read`, `boards:write`, `pins:read`, `pins:write`,
`board_pins:write`, `user_accounts:read`.

### Fallback manual (sem listener)

Se o redirect falhar (página em branco/erro), copie o valor de `?code=...`
direto da barra de endereço e troque manualmente:

```bash
./.venv/bin/python scripts/pinterest_auth.py --code SEU_CODE \
  --redirect-uri http://localhost:8765/
```

## Passo 4 — Trocar o code por token e salvar no `.env`

Com o `code` capturado:

```bash
CODE=$(./.venv/bin/python -c "import json;print(json.load(open('/tmp/pinterest_code.json'))['code'])")
./.venv/bin/python scripts/pinterest_auth.py --code "$CODE" \
  --redirect-uri http://localhost:8765/
```

O script (`scripts/pinterest_setup.py:exchange_code`) faz a troca na produção,
imprime os escopos concedidos e grava no `.env`:

```
PINTEREST_ACCESS_TOKEN=pina_...
PINTEREST_REFRESH_TOKEN=pinr_...
```

## Passo 5 — Testar a publicação

```bash
# Só valida conexão e mostra o que faria
./.venv/bin/python scripts/pinterest_publish.py --dry-run --last 3

# Publica 1 pin real
./.venv/bin/python scripts/pinterest_publish.py --last 1
```

Esperado: `✅ Pin criado: <pin_id>` e o registro gravado em
`dashboard/data/pinterest_published.json`.

---

## Depois: publicar a partir do Render

O `redirect_uri` só é usado **uma vez**, na autorização. O token obtido vale
de qualquer lugar (Render, cron, local) e a renovação via
`grant_type=refresh_token` não usa redirect URI.

Porém o `render.yaml:52` declara `PINTEREST_ACCESS_TOKEN` como `sync: false`
(env var fixa no painel do Render). Depois de gerar o token novo:

1. Copie o valor de `PINTEREST_ACCESS_TOKEN` e `PINTEREST_REFRESH_TOKEN`
2. Atualize as env vars em https://dashboard.render.com/ → serviço
   `blog-dolar-dashboard` → **Environment**
3. Faça redeploy

### Re-autorizar sem o PC local (futuro)

Registrar também no app:
```
https://blog-dolar-dashboard.onrender.com/api/pinterest/oauth/callback
```
e criar essa rota no dashboard para trocar o `code` e salvar em
`pinterest_config.json` (disco persistente, `render.yaml:79`). O
`dashboard/routes/pinterest.py:23` já lê `access_token` desse arquivo como
fallback do `.env`.

---

## Referências

- `docs/SETUP_PINTEREST.md` — visão geral do setup
- `docs/PINTEREST_STATUS.md` — status do trial/acesso
- `scripts/pinterest_auth.py` — helper OAuth
- `scripts/pinterest_publish.py` — publicador automático
- https://developers.pinterest.com/docs/getting-started/connect-app/
