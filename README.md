# Blog em Dolar

Sistema automatizado para criar e monetizar blogs em dolar usando IA gratuita.

## Estrutura

```
blog-dolar/
├── config/
│   └── config.yaml          # Configuracoes
├── scripts/
│   ├── gerar_artigos.py     # Gera conteudo com Gemini
│   ├── publicar_wp.py       # Publica no WordPress
│   ├── instalar_adcash.py   # Configura anuncios
│   └── pipeline.py          # Orquestrador principal
├── articles/                # Artigos gerados
├── logs/                    # Logs de execucao
├── venv/                    # Ambiente virtual
└── setup.sh                 # Instalacao
```

## Inicio Rapido

### 1. Configurar

```bash
# Ativar ambiente
source venv/bin/activate

# Configurar Gemini API (free)
export GEMINI_API_KEY="sua_chave_aqui"
# Obtenha em: https://aistudio.google.com/apikey

# Editar config do WordPress
nano config/config.yaml
```

### 2. Gerar Artigos

```bash
# Gera topicos + 2 artigos
python scripts/pipeline.py

# Ou modo interativo
python scripts/gerar_artigos.py
```

### 3. Publicar no WordPress

```bash
# Publica como draft
python scripts/publicar_wp.py
```

### 4. Instalar Anuncios

```bash
# Mostra guia do AdCash
python scripts/instalar_adcash.py
```

### 5. Agendamento Automatico

```bash
# Roda a cada X horas
python scripts/pipeline.py --schedule
```

## Configuracao Detalhada

### Gemini API (100% Free)

1. Acesse https://aistudio.google.com/apikey
2. Crie uma chave (sem custo)
3. Exporte: `export GEMINI_API_KEY=AIzaSy...`

Limite free: 60 requests/minuto (suficiente para 100+ artigos/dia)

### WordPress App Password

1. WP Admin > Usuarios > Perfil
2. Secao "Chaves de Aplicativo"
3. Crie uma nova chave
4. Copie para config.yaml

### AdCash

1. Crie conta: https://adcash.com
2. Adicione seu site
3. Pegue o codigo da tag
4. Instale via plugin WPCode ou Ad Inserter

## Fluxo Automatico

```
┌─────────────────┐
│  Gera Topicos   │  ← Gemini API (free)
└────────┬────────┘
         │
┌────────▼────────┐
│  Gera Artigos   │  ← Gemini API (free)
└────────┬────────┘
         │
┌────────▼────────┐
│  Publica WP     │  ← WordPress API
└────────┬────────┘
         │
┌────────▼────────┐
│  Insere Anuncios│  ← AdCash
└────────┬────────┘
         │
┌────────▼────────┐
│  Distribui      │  ← Facebook/Pinterest
└─────────────────┘
```

## Ferramentas 100% Free

| Funcao | Ferramenta | Custo |
|--------|-----------|-------|
| Conteudo IA | Google Gemini API | $0 |
| CMS | WordPress | $0 |
| Anuncios | AdCash | $0 |
| SEO | RankMath (plugin) | $0 |
| Analytics | Google Analytics | $0 |
| Social | n8n (self-hosted) | $0 |

## Dicas

1. **Foco em ingles**: EUA paga 3-10x mais que Brasil
2. **Conteudo evergreen**: Artigos que duram anos
3. **Consistencia**: 2 artigos/dia minimo
4. **Diversifique nichos**: Nao dependa de um so
5. **SEO basico**: Use RankMath para otimizar

## Comandos Uteis

```bash
# Gerar 5 artigos de uma vez
python scripts/gerar_artigos.py

# Listar artigos gerados
ls -la articles/

# Verificar conexao WP
python scripts/publicar_wp.py

# Ajuda
python scripts/pipeline.py --help
```
