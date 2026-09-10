# Pinterest API — Setup e Automação

## Situação atual

- **App ID**: 1607290
- **Status**: Trial pendente (aguardando aprovação)
- **Client Secret**: Indisponível até aprovação
- **Permissões atuais**: Só leitura (pins:read, boards:read)
- **Token atual**: Expirado

## Quando o trial for aprovado:

### 1. Copiar o Client Secret
1. Vá em: https://developers.pinterest.com/apps/
2. Clique no app "Blog em Dolar"
3. Copie o **Client Secret** (agora estará disponível)

### 2. Gerar token com permissões de escrita
Abra no navegador (substitua SEU_CLIENT_ID pelo Client ID 1607290):
```
https://www.pinterest.com/oauth/authorize/?client_id=1607290&response_type=code&redirect_uri=https://localhost&scope=boards:read,pins:read,pins:write,board_pins:write
```

3. Autorize o app
4. Copie o `code` da URL de redirecionamento

### 3. Trocar code por token
```bash
curl -X POST https://api.pinterest.com/v5/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=SEU_CODE" \
  -d "redirect_uri=https://localhost" \
  -u "1607290:SEU_CLIENT_SECRET"
```

### 4. Salvar no .env
```
PINTEREST_ACCESS_TOKEN=pina_...
PINTEREST_REFRESH_TOKEN=pinr_...
PINTEREST_CLIENT_ID=1607290
PINTEREST_CLIENT_SECRET=...
```

### 5. Descobrir Board ID
```bash
python scripts/pinterest_setup.py
```

### 6. Criar pins
```bash
# Dry run (ver o que seria criado)
python scripts/pinterest_publish.py --dry-run --all

# Publicar pins para todos os artigos
python scripts/pinterest_publish.py --all

# Publicar apenas últimos 3
python scripts/pinterest_publish.py --last 3
```

## Automação via pipeline

O pipeline do dashboard já cria pins automaticamente quando publica artigos.
Basta configurar PINTEREST_ACCESS_TOKEN e PINTEREST_BOARD_ID no .env.
