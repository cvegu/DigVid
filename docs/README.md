# 🎵 Sonivo - Generador de Videos Musicales para Instagram

Aplicación web para generar videos de música estilo vinilo para Instagram (1080x1350px) con fondo animado, portada girando y metadata del audio.

## ✨ Características

- **Modo Individual**: Genera un video a la vez
- **Modo Batch**: Procesa hasta 10 canciones simultáneamente
- **Extracción automática de metadata**: Artista, título, portada desde archivos de audio
- **Selección visual de segmentos**: Waveform interactivo para elegir qué parte de la canción usar
- **Fondo animado dinámico**: Colores extraídos de la portada del álbum
- **Reproductor de audio integrado**: Para previsualizar el segmento seleccionado
- **Export optimizado**: Videos en formato vertical Instagram (1080x1350px)

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.11+
- FFmpeg instalado en el sistema

### Instalación

1. **Clonar el repositorio**:
```bash
git clone https://github.com/cvegu/Sonivo.git
cd Sonivo
```

2. **Crear entorno virtual**:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

4. **Instalar FFmpeg**:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# Descargar desde https://ffmpeg.org/download.html
```

5. **Iniciar el servidor**:
```bash
./start.sh  # macOS/Linux
# o
start.bat   # Windows
# o manualmente
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

6. **Abrir en el navegador**:
```
http://localhost:8000
```

## 📖 Uso

### Modo Individual

1. **Subir archivo de audio**: Arrastra un archivo MP3, WAV, FLAC, etc. a la zona de upload
2. **Editar metadata**: La aplicación extraerá automáticamente artista, título y portada. Puedes editarlos manualmente.
3. **Seleccionar segmento**: Usa el waveform visual para elegir qué parte de la canción usar (por defecto 30 segundos)
4. **Reproducir preview**: Haz click en "Reproducir" para escuchar el segmento seleccionado
5. **Generar video**: Haz click en "Generar Video" y espera a que se complete (puede tardar varios minutos)
6. **Descargar**: Descarga el video generado

### Modo Batch

1. **Subir múltiples archivos**: Arrastra hasta 10 archivos de audio
2. **Configurar tiempos por defecto**: Establece tiempos de inicio y fin para todas las canciones
3. **Personalizar canciones**: Edita metadata individual de cada canción si es necesario
4. **Generar videos**: Haz click en "Generar Videos" y espera a que se procesen todos
5. **Descargar**: Descarga videos individuales o un ZIP con todos los videos y una lista de canciones

## 🛠️ Características Técnicas

- **Formato de video**: MP4 (H.264) en 1080x1350px (formato vertical Instagram)
- **Calidad**: CRF 18 (alta calidad), preset slow
- **Audio**: AAC 192kbps
- **FPS**: 30
- **Rotación del vinilo**: 33⅓ RPM (velocidad estándar de LP)
- **Fondo animado**: Gradiente animado tipo "liquid glass" con colores de la portada
- **Formatos de audio soportados**: MP3, WAV, FLAC, M4A, OGG, AAC
- **Formatos de imagen soportados**: JPG, PNG, GIF, WEBP

## 📁 Estructura del Proyecto

```
Sonivo/
├── app/
│   ├── main.py                    # FastAPI app principal
│   ├── routes/
│   │   └── video.py               # Endpoints de la API
│   ├── services/
│   │   ├── audio_processor.py     # Extracción de metadata y waveform
│   │   ├── video_generator.py     # Generación de video (core)
│   │   └── image_processor.py     # Procesamiento de portadas
│   └── templates/
│       └── index.html             # Interfaz web
├── static/
│   ├── css/
│   │   └── style.css              # Estilos (tema oscuro minimalista)
│   └── js/
│       └── app.js                 # Lógica del frontend
├── fonts/                         # Fuentes Helvetica (fallback)
├── uploads/                       # Archivos temporales subidos
├── outputs/                       # Videos generados
├── docs/                          # Documentación
├── requirements.txt               # Dependencias Python
└── README.md                      # Este archivo (en raíz)
```

## 📚 Documentación

| Documento | Descripción |
|-----------|-------------|
| [TECHNICAL_DETAILS.md](TECHNICAL_DETAILS.md) | Arquitectura, componentes, flujo de datos, debugging |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Cómo llevar la app a producción (Railway, Render, etc.) |
| [benchmark_report.md](benchmark_report.md) | Resultados de benchmarks de generación de video |

## ⚠️ Notas Importantes

- **Tiempo de generación**: La generación de video puede tardar varios minutos dependiendo de la duración del segmento
- **FFmpeg requerido**: Se requiere FFmpeg instalado en el sistema para la generación de video
- **Archivos temporales**: Los archivos subidos se guardan en `uploads/` y los videos generados en `outputs/`
- **Límite de batch**: El modo batch procesa hasta 10 canciones a la vez

## 📝 Licencia

Este proyecto es de código abierto. Consulta el archivo LICENSE para más detalles.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o pull request en el repositorio.
