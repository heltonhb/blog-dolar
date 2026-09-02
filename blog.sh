#!/bin/bash
# Blog em Dolar - Atalho para executar scripts
# Uso: ./blog.sh [comando]

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/venv/bin/activate" 2>/dev/null || true

case "${1:-help}" in
    setup)
        echo "Executando setup..."
        bash "$DIR/setup.sh"
        ;;
    
    gerar|generate)
        echo "Gerando artigos..."
        python3 "$DIR/scripts/gerar_artigos.py"
        ;;
    
    publicar|publish)
        echo "Publicando no WordPress..."
        python3 "$DIR/scripts/publicar_wp.py"
        ;;
    
    adcash|ads)
        echo "Configurando AdCash..."
        python3 "$DIR/scripts/instalar_adcash.py"
        ;;
    
    pipeline|run)
        echo "Executando pipeline completo..."
        python3 "$DIR/scripts/pipeline.py"
        ;;
    
    schedule|auto)
        echo "Iniciando modo agendador..."
        python3 "$DIR/scripts/pipeline.py" --schedule
        ;;
    
    help|*)
        echo ""
        echo "Blog em Dolar - Comandos:"
        echo ""
        echo "  ./blog.sh setup      - Configurar ambiente"
        echo "  ./blog.sh gerar      - Gerar artigos com IA"
        echo "  ./blog.sh publicar   - Publicar no WordPress"
        echo "  ./blog.sh adcash     - Configurar anuncios"
        echo "  ./blog.sh pipeline   - Executar tudo"
        echo "  ./blog.sh schedule   - Modo automatico"
        echo ""
        ;;
esac
