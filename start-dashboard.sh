#!/bin/bash
# Blog em Dolar - Iniciar Dashboard
# Uso: ./start-dashboard.sh

cd /home/helton/blog-dolar
source venv/bin/activate

echo "🚀 Iniciando Dashboard do Blog em Dolar..."
echo "📊 Acesse: http://localhost:5001"
echo "🛑 Para parar: Ctrl+C"
echo ""

python3 dashboard/app.py
