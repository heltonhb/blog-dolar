# Guia Operacional de Monetização — Opções A (Afiliados) e C (Display Ads Alternativos)

**Data:** 2026-10-03  
**Blog:** Tech Tips (`techtips.dpdns.org`)  
**Estratégia:** Monetização imediata em Dólar (USD) mantendo conformidade total com o Google AdSense.

---

## 1. Visão Geral da Arquitetura de Receita

```
                 TRÁFEGO DO BLOG (EUA / TIER-1)
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
┌──────────────────────────────┐        ┌──────────────────────────────┐
│  OPÇÃO A: AFILIADOS EM USD   │        │  OPÇÃO C: DISPLAY ADS SEGURO │
│                              │        │                              │
│ • Amazon Associates (EUA)    │        │ • Monetag (Native Banners)   │
│ • VPNs & SaaS (NordVPN/etc.) │        │ • Infolinks (InText/InFold)  │
│                              │        │                              │
│ Ganho: $10 a $50 por venda   │        │ Ganho: CPM passivo em dólar  │
│ Risco AdSense: ZERO          │        │ Risco AdSense: ZERO (se sem  │
│                              │        │ popunders invasivos)         │
└──────────────────────────────┘        └──────────────────────────────┘
```

---

## 2. OPÇÃO A: Amazon Associates EUA (Passo a Passo)

### 2.1 Por que a Amazon EUA é a melhor opção inicial?
- Um blog com 100 visitas/dia pode gerar **$50 a $150/mês** com 2 ou 3 vendas de hardware (laptops, monitores, SSDs, fones).
- Seus artigos já têm o conteúdo e a autoridade necessários para guias de compra.
- Totalmente compatível com as regras de SEO do Google (`rel="nofollow sponsored"`).

### 2.2 Passo a Passo para Criar a Conta
1. Acesse: **[affiliate-program.amazon.com](https://affiliate-program.amazon.com)** (Atenção: use o site `.com` dos EUA, não `.com.br`).
2. Faça login com sua conta Amazon ou crie uma nova conta dedicada.
3. Preencha os dados do site:
   - **Website List:** `https://techtips.dpdns.org`
   - **What are your websites about?:**  
     `Practical technology guides, PC hardware comparisons, student gadget buying advice, and computer tutorials.`
   - **Which topics best describe your websites?:** `Computers / Electronics / Technology`.
   - **What type of items do you intend to list?:** `Electronics, Computers & Office, Software`.
   - **How do you drive traffic?:** `SEO, Social Networks (Pinterest), Content Marketing`.
4. Defina seu **Store ID (Associate Tag)**:
   - Exemplo sugerido: `techtips0a-20` (a Amazon sempre adiciona `-20` no final das tags dos EUA).

### 2.3 Como Receber os Ganhos em Dólar
A Amazon US paga por depósito direto (ACH) em contas bancárias americanas (mínimo de saque: apenas **$10**):
- Você pode usar os dados de recebimento em dólar de contas globais brasileiras como:
  - **Nomad**
  - **Wise (antiga TransferWise)**
  - **Avenue**
  - **Payoneer**
- Na seção *Payment Method*:
  - Selecione **Direct Deposit (ACH)**.
  - Insira o *Routing Number* (geralmente 9 dígitos) e o *Account Number* da sua conta em USD.

### 2.4 Entrevista Fiscal (Tax Interview - W-8BEN)
Como você reside fora dos EUA, a Amazon exige preencher o formulário W-8BEN eletrônico (leva 3 minutos):
- **Tax Classification:** Individual
- **Are you a US person?:** No
- **Permanent Address:** Seu endereço real no Brasil.
- **TIN (Tax Identification Number):**
  - Marque: *I have a Non-US TIN*.
  - Digite seu **CPF**.
- **Claim of Tax Treaty Benefits:** O Brasil não possui tratado geral de isenção de royalties, mas para serviços prestados fora dos EUA e revenda de afiliados sem presença física nos EUA, a taxa padrão é informada e não há burocracia extra.
- Assine eletronicamente digitando seu nome completo.

### 2.5 Regra Crucial da Amazon (3 Vendas em 180 Dias)
- A Amazon aprova o cadastro imediatamente para você começar a divulgar links.
- Ela exige que você faça **3 vendas qualificadas dentro de 180 dias**.
- Após a 3ª venda, um funcionário da Amazon revisa o site para confirmar se o disclaimer legal está visível.  
  *(Nosso sistema já insere o disclaimer automaticamente em todos os artigos).*

### 2.6 Status Atual e Configuração no Sistema
A sua tag está configurada no `.env`:
```bash
AMAZON_ASSOCIATE_TAG=heltonhb-20
```

Os cartões responsivos e o disclaimer legal da FTC/Amazon já foram gerados e sincronizados:
- **Artigos locais (.md):** 4 guias com 15 produtos mapeados.
- **Posts vivos no WordPress:** Sincronizados via REST API com tag ativa e links `rel="nofollow sponsored"`.
- **CSS no ar:** Entregue via mu-plugin ativo (`techtips.dpdns.org/htdocs/wp-content/mu-plugins/tech-tips-ga4-seo.php`).

Comandos operacionais:
```bash
# 1. Injetar em todos os artigos locais
python3 scripts/affiliate_manager.py --inject-all

# 2. Publicar/sincronizar com os posts vivos do WordPress
python3 scripts/affiliate_manager.py --wp

# 3. Auditar conformidade dos links nos posts vivos
python3 scripts/affiliate_manager.py --check-wp

# 4. Deploy do mu-plugin (inclui o tracking de cliques `affiliate_click`)
python3 scripts/deploy_muplugin.py
python3 scripts/deploy_muplugin.py --check
```

### 2.7 Medindo receita: evento `affiliate_click` no GA4
O bloco 8 do mu-plugin dispara `affiliate_click` em todo clique de saída para
`amazon.*` ou `nordvpn`, com parâmetros:

| Parâmetro | Conteúdo |
|---|---|
| `affiliate_network` | `amazon` ou `nordvpn` |
| `link_url` | URL clicada |
| `product_title` | Título do cartão (vazio fora de cartão) |
| `page_path` | Artigo de origem |

No GA4: Relatórios → Engajamento → Eventos → `affiliate_click`, segmente por
`page_path` para saber **qual artigo gera receita** e por `product_title` para
saber **qual produto**. Sem isso, a meta dos 180 dias é uma caixa-preta.

---

## 3. OPÇÃO A: Afiliados de VPN e Segurança (SaaS)

Para o artigo de privacidade online (`how-to-protect-your-digital-privacy-online.md`), os programas de VPN pagam comissões excelentes:
- **NordVPN**: Paga de 40% a 100% no 1º mês + 30% de renovação vitalícia.
- **Surfshark**: Paga até 40% de revshare ou CPA fixo de $20 a $36 por venda.
- **Onde se cadastrar:**
  - [CJ Affiliate (cj.com)](https://www.cj.com)
  - [Impact.com](https://impact.com)
  - Ou diretamente em [nordvpn.com/affiliate](https://nordvpn.com/affiliate/)
- **Como ativar no blog:**
  Adicione o link do seu convite no `.env`:
  ```bash
  NORDVPN_AFFILIATE_URL=https://go.nordvpn.net/aff_c?offer_id=...
  ```
  E sincronize:
  ```bash
  python3 scripts/affiliate_manager.py --inject-all
  python3 scripts/affiliate_manager.py --wp
  ```

---

## 4. OPÇÃO C: Monetag (Display Ads Imediato)

### 4.1 Por que o Monetag?
- Aprovação em **menos de 5 minutos** (sem esperar aprovação humana).
- Sem exigência de volume mínimo de tráfego.
- Saque mínimo de **$5** via PayPal, Payoneer, Skrill, USDT.

### 4.2 Passo a Passo para Cadastro
1. Acesse: **[monetag.com](https://monetag.com)** e clique em **Sign Up as Publisher**.
2. Preencha seus dados cadastrais e confirme o e-mail.
3. No painel, clique em **Add Site**:
   - Insira: `https://techtips.dpdns.org`
   - Baixe o arquivo de verificação HTML ou use a meta tag de verificação.

### 4.3 Formatos Permitidos e Formatos PROIBIDOS (AdSense Safe)
> [!WARNING]
> Enquanto o Google AdSense estiver em revisão, siga rigorosamente estas regras para não ter seu site reprovado pelo Google:

- ✅ **FORMATOS PERMITIDOS (Seguros):**
  - **Native Banner:** Formato de recomendação de artigos com cards discretos. Coloque abaixo do artigo.
  - **In-Page Push:** Notificação sutil que desliza no canto da tela, fácil de fechar.
- ❌ **FORMATOS PROIBIDOS (Bloqueiam o AdSense):**
  - **Popunder ("OnClick"):** Abre janelas por trás ao clicar em qualquer lugar da tela. O Google penaliza imediatamente.
  - **Direct Link:** Links de redirecionamento enganosos.

### 4.4 Ativação no Blog
Após criar uma zona do tipo *In-Page Push* ou *Native Banner* no painel do Monetag:
1. Copie o **Zone ID** numérico gerado.
2. Adicione no arquivo `.env`:
   ```bash
   MONETAG_TAG_ID=1234567
   ```
3. Envie para o servidor ativo:
   ```bash
   python3 scripts/deploy_muplugin.py
   ```

---

## 5. OPÇÃO C: Infolinks (Anúncios Contextuais In-Text)

### 5.1 Como Funciona
O Infolinks identifica palavras-chave relevantes nos artigos (ex: "SSD", "laptop", "router") e aplica um sublinhado pontilhado discreto. Quando o usuário passa o mouse sobre a palavra, um preview do anúncio aparece. Além disso, exibe o **InFold** (banner sutil no rodapé da página).

- **Aprovação:** 24h a 48h.
- **Conflito com o AdSense:** **Zero.** O próprio Google AdSense permite Infolinks rodando no mesmo site.
- **Saque mínimo:** $50 via PayPal ou Payoneer.

### 5.2 Passo a Passo
1. Acesse: **[infolinks.com/join-us](https://infolinks.com/join-us)**.
2. Cadastre o domínio `https://techtips.dpdns.org`.
3. Quando a conta for aprovada, você receberá o **Publisher ID (PID)**.
4. Adicione no `.env`:
   ```bash
   INFOLINKS_PID=seu_pid_aqui
   ```
5. Envie para o servidor ativo:
   ```bash
   python3 scripts/deploy_muplugin.py
   ```

---

## 6. Ferramentas e Scripts Criados no Repositório

| Arquivo | Função |
| :--- | :--- |
| [`scripts/affiliate_manager.py`](file:///home/helton/blog-dolar/scripts/affiliate_manager.py) | Utilitário CLI para gerenciar, injetar e sincronizar cartões da Amazon/VPN localmente e no WordPress vivo. |
| [`scripts/deploy_muplugin.py`](file:///home/helton/blog-dolar/scripts/deploy_muplugin.py) | Faz o deploy seguro do mu-plugin no addon domain da InfinityFree com backup e rollback automático. |
| [`scripts/tech-tips-ga4-seo.php`](file:///home/helton/blog-dolar/scripts/tech-tips-ga4-seo.php) | Plugin WordPress (mu-plugin) com estilos CSS dos cards, AdSense, GA4 e hooks de Monetag e Infolinks. |
| [`.env.example`](file:///home/helton/blog-dolar/.env.example) | Modelo atualizado com as chaves `AMAZON_ASSOCIATE_TAG`, `NORDVPN_AFFILIATE_URL`, `MONETAG_TAG_ID` e `INFOLINKS_PID`. |

---

## 7. Comandos Úteis do Gerenciador de Afiliados

```bash
# 1. Escanear quais artigos possuem produtos identificados
python3 scripts/affiliate_manager.py --scan

# 2. Testar injeção local sem alterar arquivos (Dry-Run)
python3 scripts/affiliate_manager.py --inject-all --dry-run

# 3. Injetar cartões e disclaimer em todos os artigos locais (.md)
python3 scripts/affiliate_manager.py --inject-all

# 4. Injetar em um artigo específico local
python3 scripts/affiliate_manager.py --inject 2026-09-01_best-budget-laptops-for-students-2026.md

# 5. Sincronizar com os posts vivos do WordPress (via REST API)
python3 scripts/affiliate_manager.py --wp

# 6. Auditar se todos os links de afiliado nos posts vivos estão corretos e seguros
python3 scripts/affiliate_manager.py --check-wp

# 7. Fazer deploy de atualizações no mu-plugin
python3 scripts/deploy_muplugin.py
```

---

## 8. Próximos Passos para o Dono do Blog

1. **Meta de 180 dias da Amazon (3 vendas):**
   - Promova ativamente os 2 posts de hardware que estão no ar (`/best-budget-laptops-for-students-2026/` e `/top-5-best-portable-power-banks-in-2026/`) criando pins visuais no Pinterest.
2. **Publicar os 2 guias adicionais de hardware:**
   - Os guias de Monitores (`best-monitors-work-from-home`) e SSDs (`nvme-ssd-vs-sata-ssd-vs-hdd`) já têm cartões prontos no repositório. Quando forem publicados no WordPress via pipeline/REST, basta rodar `python3 scripts/affiliate_manager.py --wp` para receberem seus links de afiliado.
3. **Opção C (Monetag / Infolinks):**
   - Se desejar monetização por visualizações (CPM) imediata enquanto aguarda o AdSense, cadastre-se no Monetag ou Infolinks e adicione os IDs no `.env`.

