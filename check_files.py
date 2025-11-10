#!/usr/bin/env python3
"""Verifica que todos los archivos necesarios estén disponibles localmente"""

import os
from pathlib import Path

required_files = [
    "app/main.py",
    "app/routes/video.py",
    "app/services/audio_processor.py",
    "app/services/video_generator.py",
    "app/services/image_processor.py",
    "app/templates/index.html",
    "static/css/style.css",
    "static/js/app.js",
]

print("Verificando archivos...")
all_ok = True
for file_path in required_files:
    path = Path(file_path)
    if path.exists():
        try:
            # Intentar leer el archivo para verificar que está disponible
            with open(path, 'r') as f:
                f.read(1)
            print(f"✅ {file_path}")
        except Exception as e:
            print(f"❌ {file_path} - Error al leer: {e}")
            all_ok = False
    else:
        print(f"❌ {file_path} - No existe")
        all_ok = False

if all_ok:
    print("\n✅ Todos los archivos están disponibles")
    exit(0)
else:
    print("\n❌ Algunos archivos no están disponibles localmente")
    print("💡 Solución: Espera a que OneDrive sincronice todos los archivos, o")
    print("   mueve el proyecto fuera de OneDrive a una carpeta local")
    exit(1)

