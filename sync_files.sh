#!/bin/bash
# Script para forzar la sincronización de archivos de OneDrive

echo "Sincronizando archivos de OneDrive..."
echo "Esto puede tardar unos minutos..."

cd "$(dirname "$0")"

# Forzar lectura de todos los archivos Python
find app -name "*.py" -exec cat {} > /dev/null 2>&1 \;

# Forzar lectura de archivos HTML/CSS/JS
find app/templates static -type f \( -name "*.html" -o -name "*.css" -o -name "*.js" \) -exec cat {} > /dev/null 2>&1 \;

echo "✅ Sincronización iniciada. Espera unos segundos..."
sleep 5

# Verificar
python3 check_files.py

