# DigVid - Generador de Videos Musicales para Instagram

Aplicación web para generar videos de música estilo vinilo para Instagram (1080x1350px) con fondo animado, portada girando y metadata del audio.

## Características

- Subida de archivos de audio (MP3, WAV, FLAC, M4A, OGG)
- Extracción automática de metadata (artista, título, portada)
- Edición manual de información y portada
- Selección de segmento de audio (segundo inicio - segundo fin)
- Generación de video con fondo animado tipo "liquid glass"
- Portada girando como vinilo
- Texto con artista y título
- Export optimizado para Instagram feed (1080x1350px)

## Instalación

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Asegurarse de tener FFmpeg instalado (requerido por MoviePy):
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# Descargar desde https://ffmpeg.org/download.html
```

## Uso

1. Instalar dependencias (recomendado usar un entorno virtual):
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Iniciar el servidor:
```bash
uvicorn app.main:app --reload
```

3. Abrir navegador en: http://localhost:8000

4. Usar la aplicación:
   - Subir un archivo de audio (drag & drop o click para seleccionar)
   - La aplicación extraerá automáticamente metadata y portada si están disponibles
   - Editar manualmente artista, título y portada si es necesario
   - Seleccionar el segmento de audio (segundos de inicio y fin)
   - Generar el video
   - Descargar el video generado

## Características Técnicas

- **Rotación del vinilo**: 33⅓ RPM (velocidad estándar de LP)
- **Formato de video**: MP4 (H.264) en 1080x1350px (formato vertical Instagram)
- **Fondo animado**: Gradiente animado tipo "liquid glass" con efecto fluido
- **Soporte de formatos de audio**: MP3, WAV, FLAC, M4A, OGG
- **Soporte de formatos de imagen**: JPG, PNG, GIF, WEBP

## Notas

- La generación de video puede tardar varios minutos dependiendo de la duración del segmento
- Se requiere FFmpeg instalado en el sistema para la generación de video
- Los archivos subidos se guardan temporalmente en la carpeta `uploads/`
- Los videos generados se guardan en la carpeta `outputs/`

## Estructura del Proyecto

```
DigVid/
├── app/
│   ├── main.py              # FastAPI app principal
│   ├── routes/
│   │   └── video.py         # Endpoints para generación de video
│   ├── services/
│   │   ├── audio_processor.py   # Extracción de metadata
│   │   ├── video_generator.py   # Generación de video con MoviePy
│   │   └── image_processor.py   # Rotación de portada
│   └── templates/
│       └── index.html       # Interfaz web
├── static/
│   ├── css/
│   │   └── style.css        # Estilos de la interfaz
│   └── js/
│       └── app.js           # Lógica del frontend
├── uploads/                 # Archivos temporales subidos
└── outputs/                 # Videos generados
```

