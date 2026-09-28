# MIGRATION_CHECKLIST — Plano G (update 2026-09-28)

## ✅ STATUS 28/09 — re-verificação completa (sem regressões)

- [x] **Suíte de testes: `81 passed`** (rodada 2 limpa; a 1ª rodada teve 18
  falhas transitórias por timeout na Postgres remota do Neon, não do código).
- [x] Varredura anti-anúncios **16/16 URLs limpas**.
- [x] Saúde do domínio novo (`scripts/saude_dominio_novo.py`): title OK,
  canonical + `og:url` = `https://techtips.dpdns.org/`, GA4 `G-G01J573W6J`,
  **0 refs a ct.ws**, robots.txt e ads.txt corretos
  (`google.com, pub-6258036451330976, DIRECT, f08c47fec0942fa0`).
- [x] Sitemap do WP: índice com 4 sub-sitemaps → **18 URLs** (11 posts, 5
  páginas, 1 categoria, 1 autor), **0 com ct.ws**.
- [x] Anti-bot AES: **Googlebot e bingbot recebem conteúdo real** (ads.txt = 59
  bytes corretos); navegador normal recebe o challenge JS. Crawlers não ficam
  bloqueados.
- [x] **Pendência opcional do repo RESOLVIDA**: `sitemap.php`, `robots.txt`,
  `robots_new.txt` e `sitemap_static.xml` já **não citam mais ct.ws**
  (contagem `grep -c 'ct.ws'` = 0 em todos).
- [~] **301 do domínio antigo — IMPOSSÍVEL de confirmar porque o host está
  FORA DO AR**: teste via `check-host.net` com 3 nós externos (Suíça, Reino
  Unido, EUA) → **"Connection timed out" nos 3**. Não é bloqueio da rede local
  do agente: `tech-tips.ct.ws` → `199.59.243.225` não responde porta 80/443
  de lugar nenhum. O `.htaccess` com o 301 está no lugar, mas não há servidor
  para servi-lo. Consequência: o Google eventualmente abandona o domínio
  antigo sozinho; só vale reimplementar o redirect se o host antigo voltar
  (ou apontar o DNS do ct.ws para a InfinityFree e redirecionar lá).
- [ ] Cadeia SSL **continua incompleta**: `openssl s_client` mostra só o cert
  folha (`CN=techtips.dpdns.org`, emissor `Let's Encrypt/YR1`) — o
  intermediário `YR1` não é enviado. Browsers e Google resolvem via AIA;
  `curl`/`requests` com verificação estrita falham (por isso os scripts usam
  contexto não verificado). Ação: painel InfinityFree → SSL/TLS.

---

## ✅ STATUS 27/09 — Etapas 5–7 executadas

- [x] SSL: certificado **Let's Encrypt** emitido (27/09, `CN=techtips.dpdns.org`).
  ⚠️ Cadeia incompleta (servidor envia só o cert folha, sem o intermediário
  `YR1`) → browsers validam via AIA, mas curl/Python com verificação estrita
  falha. Scripts do projeto (antibot/fetch_wp_post/internal_links) usam contexto
  não verificado, mantendo o padrão já existente.
- [x] Etapa 5: `etapa5_redirect_301.py` executado — `.htaccess` 301 instalado no
  htdocs antigo (backup em `scripts/_backup_htaccess_antigo_pre301`); robots.txt
  antigo agora aponta para o sitemap novo. Confirmado que `htdocs/` é o site
  antigo (mesmo banco `if042797779_wp631`, prefixo `wptl_`).
- [x] `SITE_URL` atualizado (`.env`, `dashboard/data/.env`, `render.yaml`) e todas
  as referências hardcoded a `tech-tips.ct.ws` trocadas no dashboard e scripts
  (constantes de migração preservadas: `publish_devto.ANTIGO_DOMINIO`, etapa4/5,
  pre_migracao, prepare_migration).
- [x] Etapa 6: Dev.to — canonicals já no domínio novo (0 a migrar);
  `internal_links.py --apply` → 11 posts com "Related Articles" no domínio novo.
- [x] Etapa 7: cache do addon vazio (nada a limpar); varredura 16/16 URLs OK;
  post verificado (canonical novo, GA4 `G-G01J573W6J`, 0 refs a ct.ws).
- [x] Testes: **47 passed**.

### Pendências
- [x] ~~Confirmar o 301 de `tech-tips.ct.ws` num browser~~ → **diagnóstico
  28/09: host antigo fora do ar (3 nós externos com timeout)**. Ver STATUS
  28/09 acima.
- [ ] **Passo 3 (USUÁRIO)**: AdSense / Search Console / Bing no domínio novo.
- [x] ~~Opcional: `sitemap.php` e `robots.txt` do repo ainda citam ct.ws~~ →
  verificado 28/09: nenhum arquivo do repo cita mais ct.ws.
- [ ] Corrigir a cadeia SSL completa no painel, se algum browser reclamar.

---

## ⚠️ STATUS 26/09 — bug crítico encontrado e corrigido

O domínio novo estava **fora do ar (HTTP 500 em tudo, inclusive /robots.txt)**.
Causa: a cópia do tema **Astra ficou incompleta** no addon — faltava
`themes/astra/inc/addons/transparent-header/classes/dynamic-css/dynamic.css.php`,
com o `require_once` estourando `Uncaught Error` no bootstrap do WP. Como a
Etapa 4 carrega `wp-load.php`, a migração de URLs nunca concluiu (o script
morria no mesmo fatal).

Correções aplicadas nesta sessão:
- [x] Tema Astra reparado: pacote oficial 4.13.10 baixado, enviado por FTP e
  extraído no servidor (ZipArchive) → `dynamic.css.php` OK (50.349 bytes)
- [x] Plugins faltantes instalados (estavam como pastas VAZIAS em wp-content):
  `contact-form-7` 6.1.7 e `wp-super-cache` 3.1.3 (download oficial + extract)
- [x] `astra-sites` fica como `astra-sites.disabled` (cópia parcial dava fatal;
  é plugin de import de templates, não é necessário)
- [x] Etapa 4 executada: search-replace `tech-tips.ct.ws`→`techtips.dpdns.org`
  em posts/guid/excerpt (57→0), postmeta (0), options (4→0); siteurl/home OK
- [x] Cache do W3TC limpo (`w3tc_flush_all()` + wipe de `wp-content/cache`)
- [x] Limpeza de ~27 arquivos de teste/debug esquecidos na raiz do addon
  (`test_*.php`, `debug.php`, `phpinfo.php`, `_probe.php`, `_migra_urls.php`…)
- [x] Verificação: **17/17 URLs do sitemap → 200, zero refs a ct.ws**;
  canonical/og:url corretos, GA4 `G-G01J573W6J` presente, robots+sitemap OK

### 🔴 BLOQUEIO 26/09 (resolvido em 27/09): SSL do addon
`https://techtips.dpdns.org` ainda serve certificado **self-signed** (curl:
"certificate subject name '*' does not match"). **Ação do usuário**: painel
InfinityFree → SSL/TLS → emitir certificado grátis para `techtips.dpdns.org`.
Sem isso, AdSense/browser rejeitam, e os scripts (REST do WP com verificação de
cert) falham ao apontar para o domínio novo.

### Próximas fases (após o SSL)
- [ ] Etapa 5: `scripts/etapa5_redirect_301.py` (301 antigo → novo)
- [ ] Etapa 6: atualizar `.env SITE_URL` + `scripts/antibot.py SITE` para o
  domínio novo; regenerar internal_links (`--apply`); Dev.to (7 canonicals);
  conferir GA4/canonical no domínio novo
- [ ] Etapa 7: `scripts/limpar_cache.py` + verificação final das 16 URLs
- [ ] Passo 3: AdSense / Search Console / Bing no domínio novo

---

# (Plano G — registro original, 24/09)

## Contexto do problema
- AdSense recusa `tech-tips.ct.ws` (ct.ws NÃO está na Public Suffix List — o
  AdSense exige domínio registrável próprio). O mesmo motivo dos bloqueios
  Pinterest/ISP.
- **Resolvido**: domínio grátis `techtips.dpdns.org` registrado no DigitalPlat
  (dpdns.org ESTÁ na PSL — verificado contra publicsuffix.org). Addon domain
  criado na InfinityFree, DNS propagado, NS válidos.

## O que JÁ foi feito (24/09)
- [x] Registro do `techtips.dpdns.org` (DigitalPlat, grátis, PSL)
- [x] Nameservers → ns1/ns2.infinityfree.com, validado no painel
- [x] Addon domain criado (pasta própria `techtips.dpdns.org/htdocs/`)
- [x] Bootstrap index.php testado → **FALHOU por design**: open_basedir prende
  o PHP do addon na pasta dele (probe executado). Copiar WP core por FTP é
  inviável (FTP da InfinityFree lento até para listar).
- [x] "Change Main Domain" não existe nesta conta (confirmado pelo usuário)

## Plano G — Softaculous + wp-config apontando pro banco existente

### Passo 1 (USUÁRIO, amanhã): instalar WP limpo no addon
1. Control Panel → Softaculous → Install WordPress
2. Domínio: `techtips.dpdns.org`, diretório: vazio (raiz)
3. **Database NOVA** (ex.: if0_42797779_wp2) — NÃO mexer na existente
4. Anotar admin user/senha
5. SSL: Control Panel → SSL/TLS → emitir certificado grátis p/ o addon

### Passo 2 (AGENT, depois do "installed"): reapontar — EM ANDAMENTO 25/09
- [x] Etapa 1: wp-config do addon → banco antigo (if042797779_wp631, prefixo
  wptl_) + WP_HOME/WP_SITEURL = https://techtips.dpdns.org. Backup do config
  Softaculous em scripts/_backup_wpconfig_addon_softaculous.php
- [x] Home do domínio novo respondendo com WP (title correto)
- [~] Etapa 2: copia_essencial.py (RETOMÁVEL — pula arquivos já copiados;
  rodar de novo até "✅ ... copiados"): tema astra + plugins (akismet,
  loginizer, loginizer-security, w3-total-cache, astra-sites, wordpress-seo,
  wp-super-cache, contact-form-7) + mu-plugins/tech-tips-ga4-seo.php.
  FTP MUITO lento (~1 arq/s) — rodar em background com timeout generoso.
- [ ] Etapa 3: etapa3_htaccess.py (PRONTO) — .htaccess permalinks WP
  (backup do W3TC herdado em scripts/_backup_htaccess_addon_w3tc)
- [ ] Etapa 4: migrar URLs no banco (CRIAR): PHP no addon com UPDATE
  wptl_options siteurl/home (já coberto pelo wp-config, mas banco também) +
  search-replace tech-tips.ct.ws→techtips.dpdns.org em wptl_posts
- [ ] Etapa 5: redirect 301 no htdocs antigo → domínio novo
- [ ] Etapa 6: regenerar internal_links (--apply no NOVO domínio), conferir
  canonical do mu-plugin (trocar hardcoded ct.ws se houver), robots,
  sitemap, GA4 (mesma tag), Dev.to canonicals (7 PUTs)
- [ ] Etapa 7: scripts/limpar_cache.py + verificação 16 URLs no novo domínio
- [ ] SSL: USUÁRIO emite no painel (SSL/TLS → techtips.dpdns.org) se ainda
  não fez — sem isso https fica self-signed e browser/AdSense rejeitam

### Passo 3 (USUÁRIO): pós-migração
1. AdSense: adicionar `techtips.dpdns.org` (agora aceita — PSL)
2. Search Console: nova propriedade + sitemap do domínio novo
3. Bing Webmaster Tools: reimportar/adicionar o domínio novo
   (BING_API_KEY e API key continuam válidos — mesma conta)

### Ordem de verificação final
- [ ] https://techtips.dpdns.org/ responde com WP (title "Tech Tips")
- [ ] 11 posts + 5 páginas no ar no domínio novo
- [ ] ct.ws → 301 → dpdns.org em todas as URLs
- [ ] Related Articles apontando pro domínio novo
- [ ] canonical/og/sitemap/robots no domínio novo
- [ ] GA4 coletando no domínio novo
- [ ] Dev.to: 7 canonicals atualizados

## Aprendizados técnicos da sessão (24/09)
- open_basedir do addon: `/php_sessions:/home/uploads:/tmp:/var/www/errors:
  /home/vol6_1/infinityfree.com/if0_42797779/techtips.dpdns.org/htdocs`
  (não dá para require() nada fora da pasta do addon)
- DOCUMENT_ROOT do addon: `/home/vol6_1/infinityfree.com/if0_42797779/
  techtips.dpdns.org/htdocs` — caminho absoluto confirmado via probe PHP
- SSL do addon é self-signed até emitir Let's Encrypt no painel
- Anti-bot AES também protege o addon domain (mesma infra)

---

# (Histórico) Checklist de Migração — ByetHost → InfinityFree

## Etapa 1: Criar Conta InfinityFree
- [x] Acessar https://www.infinityfree.com/
- [x] Criar conta gratuita
- [x] Criar novo site
- [x] Anotar credenciais de FTP (host, user, pass)
- [x] Anotar dados do MySQL (host, user, pass, db)

## Etapa 2: Instalar WordPress
- [x] Softaculous → WordPress instalado
- [x] Tema Astra, permallinks /%year%/%monthnum%/%day%/%postname%/
- [x] Título: Tech Tips

## Etapa 3: Conteúdo migrado via pipeline (repúblicas REST)
