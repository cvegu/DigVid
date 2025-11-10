#!/usr/bin/env python3
"""Script de prueba para verificar el endpoint de upload"""

import requests
import os

# Crear un archivo de prueba pequeño
test_file = "test_audio.mp3"
if not os.path.exists(test_file):
    # Crear un archivo dummy
    with open(test_file, "wb") as f:
        f.write(b"fake mp3 content")

try:
    url = "http://localhost:8000/api/upload/audio"
    with open(test_file, "rb") as f:
        files = {"file": (test_file, f, "audio/mpeg")}
        response = requests.post(url, files=files, timeout=30)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

