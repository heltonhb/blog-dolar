# Guia Completo: Configurar Ad Inserter Corretamente
# ================================================

## PASSO 1: ATIVAR O PLUGIN
1. Acesse: https://tech-tips.byethost4.com/wp-admin
2. Vá em: Plugins > Plugins Instalados
3. Encontre "Ad Inserter"
4. Clique em "Ativar"

## PASSO 2: ACESSAR CONFIGURAÇÕES
1. Vá em: Settings > Ad Inserter
2. Você verá 16 blocos (Block 1 até Block 16)

## PASSO 3: CONFIGURAR BLOCO 1 (HEADER)
1. Clique no bloco "Block 1"
2. Configure:
   - Name: Header Banner
   - Activation: ✅ Enabled
   - Posts: ✅ Home, ✅ Posts
   - Pages: ✅ Static
   - Alignment: Center
   - Code:
```html
<script async data-cfasync="false" src="https://cdn.ad-cash.com/adcash.js"></script>
```

## PASSO 4: CONFIGURAR BLOCO 2 (SIDEBAR)
1. Clique no bloco "Block 2"
2. Configure:
   - Name: Sidebar Rectangle
   - Activation: ✅ Enabled
   - Posts: ✅ Home, ✅ Posts
   - Pages: ✅ Static
   - Widget: ✅ Right Sidebar
   - Code:
```html
<div style="width:300px; text-align:center;">
<script async data-cfasync="false" src="https://cdn.ad-cash.com/adcash.js"></script>
</div>
```

## PASSO 5: CONFIGURAR BLOCO 3 (IN-CONTENT)
1. Clique no bloco "Block 3"
2. Configure:
   - Name: In-Content Ad
   - Activation: ✅ Enabled
   - Posts: ✅ Posts
   - Pages: ✅ Static
   - Insertion: After paragraph 2
   - Code:
```html
<script async data-cfasync="false" src="https://cdn.ad-cash.com/adcash.js"></script>
```

## PASSO 6: CONFIGURAR BLOCO 4 (FOOTER)
1. Clique no bloco "Block 4"
2. Configure:
   - Name: Footer Banner
   - Activation: ✅ Enabled
   - Posts: ✅ Home, ✅ Posts
   - Pages: ✅ Static
   - Insertion: Before </body>
   - Code:
```html
<script async data-cfasync="false" src="https://cdn.ad-cash.com/adcash.js"></script>
```

## PASSO 7: SALVAR CONFIGURAÇÕES
1. Clique em "Save" ou "Save Changes"
2. Aguarde a mensagem de sucesso

## PASSO 8: VERIFICAR INSTALAÇÃO
1. Acesse: https://tech-tips.byethost4.com/check-ad-inserter.php
2. Verifique se todos os blocos estão "HABILITADO"

## CHECKLIST DE VERIFICAÇÃO
- [ ] Plugin Ad Inserter está ATIVO
- [ ] Bloco 1 configurado e habilitado
- [ ] Bloco 2 configurado e habilitado
- [ ] Bloco 3 configurado e habilitado
- [ ] Bloco 4 configurado e habilitado
- [ ] Código AdInserter inserido em todos os blocos
- [ ] Configurações salvas

## SOLUÇÃO DE PROBLEMAS

### Problema: Plugin não aparece na lista
Solução: Verifique se o diretório ad-inserter existe em wp-content/plugins/

### Problema: Blocos não aparecem
Solução: Limpe o cache do navegador (Ctrl+F5)

### Problema: Configurações não salvam
Solução: Verifique se há permissões de escrita no banco de dados

### Problema: Anúncios não aparecem
Solução: Verifique o console do navegador (F12) para erros

## PRÓXIMOS PASSOS APÓS CONFIGURAÇÃO
1. Criar conta no AdCash: https://adcash.com/publishers/signup
2. Adicionar seu site no AdCash
3. Copiar o código de rastreamento
4. Substituir o código placeholder pelo código real do AdCash
5. Publicar artigos para gerar tráfego
