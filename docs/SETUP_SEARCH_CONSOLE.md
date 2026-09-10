# Google Search Console — Setup Automatizado

## O que você precisa fazer (1 vez só):

### 1. Criar projeto no Google Cloud
1. Acesse: https://console.cloud.google.com
2. Crie um novo projeto (ex: "blog-dolar-indexing")
3. Ative as APIs:
   - **Search Console API** → https://console.cloud.google.com/apis/library/searchconsole.googleapis.com
   - **Indexing API** → https://console.cloud.google.com/apis/library/indexing.googleapis.com

### 2. Criar Service Account
1. Vá em: IAM & Admin → Service Accounts
2. Clique "Create Service Account"
3. Nome: `blog-indexer`
4. Clique "Create and Continue"
5. Role: **Owner** (ou "Service Account User")
6. Clique "Done"
7. Na lista, clique no email do service account
8. Vá em "Keys" → "Add Key" → "Create new key" → **JSON**
9. Baixe o arquivo JSON

### 3. Salvar as credenciais
Copie o arquivo JSON baixado para:
```
/home/helton/blog-dolar/google-search-console.json
```

### 4. Adicionar como Proprietário no Search Console
1. Acesse: https://search.google.com/search-console
2. Selecione a propriedade `tech-tips.byethost4.com`
3. Vá em Configurações → Usuários e propriedades
4. Clique "Adicionar usuário"
5. Cole o email do service account (algo como `blog-indexer@projetoid.iam.gserviceaccount.com`)
6. Permissão: **Proprietário**
7. Clique "Adicionar"

### 5. Rodar o indexer
```bash
cd /home/helton/blog-dolar
source venv/bin/activate
python scripts/index_search_console.py
```

---

## Verificação automática

Depois de salvar o JSON, rode:
```bash
python scripts/verify_search_console.py
```

Ele vai:
- Testar a conexão com a API
- Listar os artigos publicados
- Solicitar indexação de todos
