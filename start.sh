#!/bin/bash

# Script para iniciar el servidor DigVid

cd "$(dirname "$0")"

# Activar entorno virtual
source venv/bin/activate

# Iniciar servidor
# Si necesitas reload durante desarrollo, usa: --reload --reload-exclude "venv/*" --reload-exclude ".venv/*"
uvicorn app.main:app --host 0.0.0.0 --port 8000

