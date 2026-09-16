# Como verificar tráfego do Pinterest no blog (guia)

> Criado em 2026-09-15. Objetivo: sair do "achismo" e medir de verdade de onde vêm as visitas.

## Diagnóstico atual (confirmado com dados reais)

1. **Board privado era a causa do 0 tráfego.** Pins em board secreto não distribuem e
   não entram no Analytics. Já tornados **públicos** + com **link direto** pro artigo
   (tech-tips.byethost4.com). Setup correto hoje.
2. **Pins públicos novos ainda não aparecem no Analytics** = NORMAL. O Pinterest
   demora dias pra distribuir pins recém-criados/movidos.
3. **3 pins públicos antigos tiveram 0 cliques de saída** = problema de link/formato
   naqueles pins específicos, não de setup. Revisar depois.
4. **Blog NÃO tinha analytics** = impossível ver tráfego por origem. Passo destravador:
   instalar Google Site Kit (GA4).

## Ordem do que fazer

### 1. Ativar Google Site Kit no WordPress (blog = tech-tips.byethost4.com)
1. `https://tech-tips.byethost4.com/wp-admin`
2. Plugins → Adicionar novo → buscar **"Site Kit by Google"** → Instalar agora → Ativar
3. **Começar** → conectar conta Google do blog
4. Selecionar **Google Analytics** (cria/conecta GA4 automaticamente); AdSense opcional
5. Autorizar quando o Google pedir
6. Pronto — GA4 injetado sem mexer em código

### 2. Onde ver o tráfego por origem (Pinterest)
- Painel Site Kit → **Traffic / Desempenho**
- OU analytics.google.com → **Aquisição → Aquisição de tráfego**
- Procurar **pinterest.com** na lista de origens (sessões > 0 = Pinterest mandando gente)

### 3. Como ler o resultado
| Resultado | Significado | Ação |
|---|---|---|
| pinterest.com com sessões > 0 | Funcionando | Escalar publicações |
| pinterest.com com 0 sessões (1+ semana com pins públicos+link) | Link/formato do pin | Revisar imagem 1000x1500, título chamativo, link |
| Nenhuma origem aparece | GA4 não ativou | Reabrir Site Kit / checar header |

## Expectativa realista de tempo
- Impressões em pins públicos novos: **1–3 dias**
- Cliques de saída: depois disso
- Primeira medição de "pinterest.com como fonte": **~1 semana** após ativar Site Kit e
  com pins públicos + link

## Nota (automação da API continua travada)
- A publicação manual funciona e é o que gera tráfego agora.
- A API (pinterest_publish.py) segue **bloqueada no trial pendente** (App 1607290) —
  sem aprovação do Pinterest não há token de escrita. Atualizar quando o trial cair.

## ✅ MIGRADO p/ OAuth de usuário (feito em 2026-09-16)
A política `iam.disableServiceAccountKeyCreation` continua bloqueando chave de
service account, então o código foi migrado para **OAuth de usuário (Desktop
Client ID)** — a política do Google Cloud não bloqueia Client ID.

**Feito no código (código pronto, falta só VOCÊ criar o Client ID no console):**
- `dashboard/google_auth.py` — reescrito: OAuth de usuário (refresh_token no
  .env) é o caminho principal; JWT service-account segue como fallback.
- `scripts/analytics_ga4.py` — flags `--auth` (gera o refresh_token 1x no
  navegador) e `--status`.
- `scripts/index_search_console.py` — passou a usar o `google_auth`
  compartilhado (mesma autorização cobre GA4 + Search Console).
- `.env.example` — bloco `GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN/GA4_PROPERTY_ID`.

### Passo a passo pra destravar (só você, no console)
1. **Criar o Desktop Client ID** em
   `console.cloud.google.com/apis/credentials` (projeto `blog-dollar-508211`):
   + Criar credenciais → **ID do cliente OAuth** → tipo de aplicativo
     **"App para computador (Desktop app)"** → criar.
   + Copiar o **Client ID** e o **Client Secret**.
2. **Ativar as APIs** em `console.cloud.google.com/apis/library`:
   - **Google Analytics Data API**
   - **Google Search Console API** (Indexing API também, se quiser indexar)
3. Colocar no `.env`: `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET`.
4. Gerar o refresh_token 1x no navegador:
   ```
   python scripts/analytics_ga4.py --auth
   ```
   (abre o navegador → autoriza → o refresh_token é gravado no `.env`.)
5. Descobrir o Property ID (ou preencher direto):
   ```
   python scripts/analytics_ga4.py --list-properties
   # ou informe o número em GA4_PROPERTY_ID no .env
   ```
6. Rodar pra buscar os dados:
   ```
   python scripts/analytics_ga4.py --days 30
   ```
7. No dashboard: página **Tráfego** → **"Atualizar agora"** — a linha
   `pinterest.com` é destacada em vermelho.

### Search Console (indexação)
Depois do passo 4 (o escopo já inclui webmasters + indexing):
   ```
   python scripts/index_search_console.py
   ```

### ✅ Setup GA4 fechado (2026-09-16, após o passo a passo)
- OAuth de usuário ativo (Gmail pessoal, escopo inclui analytics.edit p/ criar).
- Propriedade do blog criada: property id `554549804`, tag `G-G01J573W6J`,
  fluxo `15790009967`, site tech-tips.byethost4.com.
- Admin **Google Analytics Admin API** foi ativada manualmente no console (sem
  ela o `--list-properties` não lista).
- Site Kit instalado no blog, apontando para a propriedade certa: settings
  `propertyID=554549804`, `measurementID=G-G01J573W6J`. O `googleTagID=GT-NC89WBXZ`
  é o tag unificado do Google cuja `googleTagContainerDestinationIDs` entrega para
  `G-G01J573W6J` — ou seja, NÃO é desvio pra outra propriedade.
- `trackingDisabled: loggedinUsers` → visitas de admins não inflam os números.
- `sources` fica 0 até a tag acumular dados; sessões reais aparecem em 1–2 dias.
  Depois: página Tráfego → "Atualizar agora".

## Integração GA4 → dashboard (feita em 2026-09-15, opção B)
Dashboard agora mede tráfego por origem (Pinterest vs Google vs Direto):
- `scripts/analytics_ga4.py` — puxa sessões por origem na **Google Analytics Data API**,
  grava cache em `dashboard/data/analytics_source.json`.
- `dashboard/google_auth.py` — auth JWT compartilhada (GA4 + Search Console), reusa a
  mesma credencial `google-search-console.json` da raiz do projeto.
- Endpoints no app.py: `/api/traffic/ga4`, `/api/traffic/ga4/refresh` (POST),
  `/api/traffic/pinterest` (destaca a linha do Pinterest).
- Template `traffic.html`: novo card "Tráfego por Origem" com cartões (sessões do
  Pinterest, total, % Pinterest) + tabela de origens + botão "Atualizar agora".
- `.env`: placeholder `GA4_PROPERTY_ID=` adicionado (linha 22).

### Para ativar (quando Site Kit estiver ativo)
1. Instalar **Site Kit by Google** no WP (gera a credencial `google-search-console.json`
   e autoriza no GA4).
2. Colocar a credencial `google-search-console.json` na raiz do projeto.
3. `python scripts/analytics_ga4.py --list-properties` (descobre o Property ID)
   OU inserir o ID numerico em `GA4_PROPERTY_ID` no `.env`.
4. Clicar **"Atualizar agora"** na página Tráfego do dashboard — os dados aparecem.
5. Confirmar Pinterest: a linha `pinterest.com` na tabela (destacada em vermelho).