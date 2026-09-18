# Checklist de Migração — ByetHost → InfinityFree

## Etapa 1: Criar Conta InfinityFree
- [ ] Acessar https://www.infinityfree.com/
- [ ] Criar conta gratuita
- [ ] Criar novo site (escolher subdomínio .epizy.com ou .rf.gd OU apontar domínio próprio)
- [ ] Anotar credenciais de FTP (host, user, pass)
- [ ] Anotar dados do MySQL (host, user, pass, db)

## Etapa 2: Instalar WordPress
- [ ] No painel InfinityFree, acessar "Software" → "Softaculous"
- [ ] Instalar WordPress (última versão)
- [ ] Acessar WP Admin e configurar:
  - [ ] Tema: Astra (gratuito, leve)
  - [ ] Permalinks: /%year%/%monthnum%/%day%/%postname%/
  - [ ] Título do site: Tech Tips
  - [ ] Remover post "Hello World" padrão

## Etapa 3: Migrar Conteúdo
### Opção A — Export/Import WordPress (se ByetHost estiver acessível via browser):
- [ ] ByetHost WP Admin → Ferramentas → Exportar → Todo conteúdo → Baixar XML
- [ ] InfinityFree WP Admin → Ferramentas → Importar → WordPress → Instalar
- [ ] Fazer upload do XML e importar

### Opção B — Republicar via Pipeline (recomendada):
- [ ] Atualizar .env com novos dados do InfinityFree:
  ```
  SITE_URL=https://SEU-SUBDOMINIO.epizy.com
  WP_USER=novo_usuario
  WP_APP_PASSWORD=nova_application_password
  FTP_HOST=novo_ftp_host
  FTP_USER=novo_ftp_user
  FTP_PASS=novo_ftp_pass
  WP_DB_HOST=novo_db_host
  WP_DB_USER=novo_db_user
  WP_DB_PASS=novo_db_pass
  WP_DB_NAME=novo_db_name
  ```
- [ ] Publicar artigos tech via dashboard pipeline

## Etapa 4: Configurar SEO
- [ ] Google Search Console → Adicionar propriedade → SEU-SUBDOMINIO.epizy.com
- [ ] Verificar via HTML tag ou DNS
- [ ] Submeter sitemap: https://SEU-SUBDOMINIO.epizy.com/wp-sitemap.xml
- [ ] Instalar plugin Yoast SEO ou RankMath (gratuito)
- [ ] Configurar robots.txt via plugin

## Etapa 5: Configurar Monetização
- [ ] AdCash: Adicionar novo site → aguardar aprovação
- [ ] Instalar plugin "Ad Inserter" via WP Admin → Plugins → Adicionar
- [ ] Configurar blocos de anúncio no Ad Inserter

## Etapa 6: Verificar Indexação (após 3-5 dias)
- [ ] Google: site:SEU-SUBDOMINIO.epizy.com → confirmar páginas indexadas
- [ ] Search Console: verificar cobertura e erros
- [ ] GA4: verificar se sessions estão sendo registradas

## Etapa 7: Atualizar Pinterest
- [ ] Atualizar link do board/perfil para SEU-SUBDOMINIO.epizy.com
- [ ] Novos pins devem apontar para SEU-SUBDOMINIO.epizy.com
- [ ] Pins antigos: Pinterest não permite editar URL destino

## Importante sobre InfinityFree:
⚠️ O InfinityFree tem challenge anti-bot similar ao ByetHost, MAS:
- ✅ Googlebot CONSEGUE resolver (executa JS) → indexação funciona
- ❌ curl/httpx NÃO conseguem → publicação via REST API precisa usar FTP
- ✅ Publicação via FTP + wp_insert_post funciona normalmente