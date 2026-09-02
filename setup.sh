#!/bin/bash
# Blog em Dolar - Setup Rapido
# Executa: bash setup.sh

set -e

echo "=========================================="
echo "  BLOG EM DOLAR - Setup Automatico"
echo "=========================================="

# Verifica Python
if ! command -v python3 &> /dev/null; then
    echo "ERRO: Python3 nao encontrado!"
    echo "Instale: sudo pacman -S python"
    exit 1
fi

echo "Python: $(python3 --version)"

# Cria virtualenv se nao existe
if [ ! -d "venv" ]; then
    echo ""
    echo "Criando ambiente virtual..."
    python3 -m venv venv
fi

# Ativa e instala dependencias
echo ""
echo "Instalando dependencias..."
source venv/bin/activate
pip install httpx pyyaml -q

echo ""
echo "Dependencias instaladas:"
pip list | grep -E "httpx|pyyaml"

# Verifica configuracao
if [ ! -f "config/config.yaml" ]; then
    echo ""
    echo "AVISO: config/config.yaml nao encontrado!"
    echo "Copie o exemplo e preencha:"
    echo "  cp config/config.yaml.example config/config.yaml"
    echo "  nano config/config.yaml"
fi

echo ""
echo "=========================================="
echo "  SETUP CONCLUIDO!"
echo "=========================================="
echo ""
echo "Proximos passos:"
echo ""
echo "  1. Configure o Gemini API:"
echo "     - Acesse: https://aistudio.google.com/apikey"
echo "     - Crie uma chave (free)"
echo "     - Exporte: export GEMINI_API_KEY=sua_chave"
echo ""
echo "  2. Configure o WordPress:"
echo "     - Crie um App Password no WP"
echo "     - Edite: config/config.yaml"
echo ""
echo "  3. Execute o pipeline:"
echo "     source venv/bin/activate"
echo "     python scripts/pipeline.py"
echo ""
echo "  4. Para agendamento automatico:"
echo "     python scripts/pipeline.py --schedule"
echo ""
