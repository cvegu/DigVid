# 🏗️ DigVid - Arquitectura y Documentación Técnica

## 📋 Índice

1. [Visión General](#visión-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Estructura del Código](#estructura-del-código)
4. [Flujo de Datos](#flujo-de-datos)
5. [Componentes Principales](#componentes-principales)
6. [Tecnologías y Dependencias](#tecnologías-y-dependencias)
7. [Problemas Conocidos y Debugging](#problemas-conocidos-y-debugging)
8. [Guía de Desarrollo](#guía-de-desarrollo)

---

## 🎯 Visión General

DigVid es una aplicación web que genera videos musicales estilo vinilo para Instagram (1080x1350px). Combina un fondo animado tipo "liquid glass", una portada de álbum girando como un vinilo, y texto con información del artista y título de la canción.

### Características Principales

- **Modo Individual**: Genera un video a la vez
- **Modo Batch**: Procesa hasta 10 canciones simultáneamente
- **Extracción automática de metadata**: Artista, título, portada desde archivos de audio
- **Selección visual de segmentos**: Waveform interactivo para elegir qué parte de la canción usar
- **Fondo animado dinámico**: Colores extraídos de la portada del álbum
- **Reproductor de audio integrado**: Para previsualizar el segmento seleccionado

---

## 🏛️ Arquitectura del Sistema

### Stack Tecnológico

```
Frontend (Cliente)
├── HTML5 (index.html)
├── CSS3 (style.css) - Estilo minimalista tipo Resident Advisor
└── JavaScript Vanilla (app.js) - Sin frameworks

Backend (Servidor)
├── FastAPI (Python) - API REST
├── MoviePy - Generación de video
├── Mutagen - Extracción de metadata de audio
├── Pillow (PIL) - Procesamiento de imágenes
└── NumPy - Operaciones numéricas y procesamiento de imágenes

Infraestructura
├── FFmpeg - Codificación de video (requerido por MoviePy)
└── Uvicorn - Servidor ASGI
```

### Arquitectura de Capas

```
┌─────────────────────────────────────┐
│   Frontend (Browser)                │
│   - UI/UX (HTML/CSS/JS)             │
│   - Estado de la aplicación         │
│   - Comunicación con API            │
└──────────────┬──────────────────────┘
               │ HTTP/JSON
               ▼
┌─────────────────────────────────────┐
│   API Layer (FastAPI)               │
│   - Routes (video.py)               │
│   - Validación de requests          │
│   - Manejo de archivos              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Service Layer                     │
│   - AudioProcessor                  │
│   - ImageProcessor                  │
│   - VideoGenerator                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   External Dependencies             │
│   - FFmpeg (video encoding)         │
│   - System Fonts (Helvetica)        │
└─────────────────────────────────────┘
```

---

## 📁 Estructura del Código

### Estructura de Directorios

```
DigVid/
├── app/
│   ├── __init__.py
│   ├── main.py                      # Punto de entrada FastAPI
│   ├── routes/
│   │   ├── __init__.py
│   │   └── video.py                 # Endpoints de la API
│   ├── services/
│   │   ├── __init__.py
│   │   ├── audio_processor.py       # Extracción de metadata y waveform
│   │   ├── image_processor.py       # Procesamiento de portadas
│   │   └── video_generator.py       # Generación de video (core)
│   └── templates/
│       └── index.html               # Interfaz web
├── static/
│   ├── css/
│   │   └── style.css                # Estilos (tema oscuro minimalista)
│   └── js/
│       └── app.js                   # Lógica del frontend
├── fonts/                           # Fuentes Helvetica (fallback)
├── uploads/                         # Archivos temporales subidos
├── outputs/                         # Videos generados
├── requirements.txt                 # Dependencias Python
├── start.sh                         # Script de inicio (macOS/Linux)
├── start.bat                        # Script de inicio (Windows)
└── README.md                        # Documentación de usuario
```

### Componentes Clave

#### 1. `app/main.py`
- **Responsabilidad**: Configuración de FastAPI, CORS, rutas estáticas
- **Endpoints principales**: 
  - `GET /` - Sirve la interfaz web
- **Configuración**: Logging, CORS middleware

#### 2. `app/routes/video.py`
- **Responsabilidad**: Endpoints de la API REST
- **Endpoints**:
  - `POST /api/upload/audio` - Subir archivo de audio
  - `POST /api/upload/cover` - Subir imagen de portada
  - `POST /api/generate` - Generar video (modo individual)
  - `POST /api/batch/generate` - Generar videos (modo batch)
  - `GET /api/download/{video_id}` - Descargar video
  - `GET /api/audio/{audio_file_id}` - Servir audio para reproducción
  - `GET /api/waveform/{file_id}` - Obtener datos del waveform
  - `GET /api/cover/{file_id}` - Obtener imagen de portada
  - `GET /api/metadata/{file_id}` - Obtener metadata del audio

#### 3. `app/services/audio_processor.py`
- **Clase**: `AudioProcessor`
- **Responsabilidad**: Extraer metadata y portada de archivos de audio
- **Métodos principales**:
  - `extract_metadata()` - Extrae artista, título, duración, álbum
  - `extract_cover()` - Extrae imagen de portada del archivo de audio
  - `generate_waveform()` - Genera datos de waveform para visualización
- **Formatos soportados**: MP3, WAV, FLAC, M4A, OGG, AAC, MP4
- **Librerías**: Mutagen, MoviePy, Pillow

#### 4. `app/services/image_processor.py`
- **Clase**: `ImageProcessor`
- **Responsabilidad**: Procesar imágenes de portada
- **Métodos principales**:
  - `prepare_cover_image()` - Redimensiona y recorta imagen a tamaño de vinilo
  - `create_placeholder_cover()` - Crea imagen placeholder cuando no hay portada
- **Tamaño de salida**: 800x800px (cuadrado para el vinilo)

#### 5. `app/services/video_generator.py`
- **Clase**: `VideoGenerator`
- **Responsabilidad**: Generar el video final combinando todos los elementos
- **Métodos principales**:
  - `generate_video()` - Método principal que orquesta la generación
  - `create_animated_background()` - Crea fondo animado con colores de la portada
  - `create_rotating_vinyl()` - Crea animación de vinilo girando
  - `create_text_overlay()` - Crea overlay de texto con artista y título
  - `extract_dominant_colors()` - Extrae colores dominantes de la portada
  - `find_font_file()` - Busca fuentes Helvetica en el sistema
  - `wrap_text()` - Envuelve texto largo en múltiples líneas
- **Especificaciones de video**:
  - Resolución: 1080x1350px (formato vertical Instagram)
  - FPS: 30
  - Códec: H.264 (libx264)
  - Audio: AAC 192kbps
  - Calidad: CRF 18 (alta calidad)
  - Preset: slow (mejor calidad, más lento)

#### 6. `static/js/app.js`
- **Responsabilidad**: Lógica del frontend, manejo de estado, UI
- **Estado de la aplicación** (`appState`):
  - `audioFileId`: ID del archivo de audio subido
  - `coverFileId`: ID de la imagen de portada
  - `audioDuration`: Duración total del audio
  - `metadata`: Artista y título
  - `mode`: 'single' o 'batch'
  - `batchSongs`: Array de canciones para modo batch
  - `waveform`: Datos del waveform
  - `audioPlayer`: Referencia al elemento `<audio>`
- **Funciones principales**:
  - `handleAudioFile()` - Procesa archivo de audio subido
  - `loadWaveform()` - Carga y visualiza waveform
  - `setupAudioPlayer()` - Configura reproductor de audio
  - `generateVideo()` - Inicia generación de video
  - `generateBatchVideos()` - Procesa múltiples videos
  - `handleDrop()` - Maneja drag & drop de archivos

---

## 🔄 Flujo de Datos

### Flujo: Generación de Video Individual

```
1. Usuario sube archivo de audio
   ↓
2. Frontend: handleAudioFile()
   - POST /api/upload/audio
   ↓
3. Backend: upload_audio()
   - Guarda archivo en uploads/
   - AudioProcessor.extract_metadata()
   - AudioProcessor.extract_cover()
   - Retorna: {file_id, metadata, cover_file_id}
   ↓
4. Frontend: Recibe metadata
   - Muestra información en UI
   - loadWaveform() → GET /api/waveform/{file_id}
   - setupAudioPlayer() → GET /api/audio/{audio_file_id}
   ↓
5. Usuario edita metadata y selecciona segmento
   - Modifica artista, título, portada
   - Selecciona start_time y end_time (visualmente en waveform)
   ↓
6. Usuario hace click en "Generar Video"
   - generateVideo()
   - POST /api/generate
     {
       audio_file_id,
       artist,
       title,
       start_time,
       end_time,
       cover_file_id
     }
   ↓
7. Backend: generate_video()
   - Valida tiempos
   - ImageProcessor.prepare_cover_image()
   - VideoGenerator.generate_video()
     ├── create_animated_background()
     ├── create_rotating_vinyl()
     ├── create_text_overlay()
     └── CompositeVideoClip() + AudioFileClip()
   - Guarda video en outputs/
   - Retorna: {video_id}
   ↓
8. Frontend: Recibe video_id
   - Muestra enlace de descarga
   - GET /api/download/{video_id}
```

### Flujo: Modo Batch

```
1. Usuario sube múltiples archivos (hasta 10)
   ↓
2. Frontend: handleBatchAudioFiles()
   - Para cada archivo: POST /api/upload/audio
   - Almacena en appState.batchSongs[]
   ↓
3. Usuario configura tiempos por defecto y nombre de carpeta
   ↓
4. Usuario hace click en "Generar Videos"
   - generateBatchVideos()
   - POST /api/batch/generate
     {
       songs: [...],
       folder_name,
       start_time,
       end_time
     }
   ↓
5. Backend: batch_generate_videos()
   - Crea carpeta en outputs/{folder_name}/
   - Para cada canción:
     - Procesa portada
     - VideoGenerator.generate_video()
     - Guarda en outputs/{folder_name}/
   - Genera lista_canciones.txt
   - Retorna: {folder_name, videos: [...], errors: [...]}
   ↓
6. Frontend: Muestra resultados
   - Descarga individual o ZIP completo
```

---

## 🧩 Componentes Principales

### 1. Fondo Animado (`create_animated_background`)

**Ubicación**: `app/services/video_generator.py`

**Funcionalidad**:
- Extrae colores dominantes de la portada usando k-means simplificado
- Crea gradiente animado con efecto "liquid glass"
- Usa `np.interp` para transiciones suaves
- Aplica filtro gaussiano para suavizar discontinuidades
- Genera frames RGB (3 canales) para compatibilidad con MoviePy

**Problemas conocidos**:
- Puede mostrar líneas de discontinuidad si los colores son muy diferentes
- Solución: Filtro gaussiano y transiciones suaves con `np.interp`

### 2. Vinilo Girando (`create_rotating_vinyl`)

**Ubicación**: `app/services/video_generator.py`

**Funcionalidad**:
- Rotación a 33⅓ RPM (velocidad estándar de LP)
- Máscara circular para forma de vinilo
- Anti-aliasing usando `Image.Resampling.BICUBIC`
- Separación de RGB y alpha para compatibilidad con MoviePy

**Problemas conocidos**:
- Si la imagen de portada no se puede cargar, puede retornar `None`
- Solución: Validación explícita y creación de placeholder

### 3. Overlay de Texto (`create_text_overlay`)

**Ubicación**: `app/services/video_generator.py`

**Funcionalidad**:
- Artista en **bold** (Helvetica-Bold)
- Título en normal (Helvetica)
- Envuelve texto largo sin cortar palabras
- Ajusta tamaño de fuente para títulos muy largos
- Centrado vertical y horizontal

**Problemas conocidos**:
- Búsqueda de fuentes puede fallar en algunos sistemas
- Solución: Múltiples fallbacks (sistema → fonts/ → default)

### 4. Waveform Visual

**Ubicación**: `static/js/app.js` (frontend) + `app/services/audio_processor.py` (backend)

**Funcionalidad**:
- Visualización de amplitud del audio
- Selección visual arrastrando handles
- Sincronización con inputs de tiempo
- Reproductor de audio integrado

**Problemas conocidos**:
- El reproductor puede no funcionar si el archivo no se carga correctamente
- Solución: Validación de `readyState` y manejo de errores

### 5. Reproductor de Audio

**Ubicación**: `static/js/app.js`

**Funcionalidad**:
- Reproduce solo el segmento seleccionado
- Pausa automáticamente al llegar a `end_time`
- Sincroniza con selección visual del waveform
- Maneja cambios dinámicos de selección durante reproducción

**Problemas conocidos**:
- Puede fallar si el endpoint `/api/audio/{file_id}` retorna 404
- Solución: URL encoding correcto y validación de archivos

---

## 🛠️ Tecnologías y Dependencias

### Backend (Python)

```python
fastapi==0.104.1          # Framework web
uvicorn[standard]==0.24.0 # Servidor ASGI
python-multipart==0.0.6   # Manejo de uploads
moviepy==1.0.3            # Generación de video
mutagen==1.47.0           # Metadata de audio
Pillow==10.1.0            # Procesamiento de imágenes
numpy==1.24.3             # Operaciones numéricas
aiofiles==23.2.1          # Operaciones de archivo asíncronas
```

### Frontend

- **HTML5**: Estructura semántica
- **CSS3**: Estilos modernos, tema oscuro minimalista
- **JavaScript Vanilla**: Sin frameworks, código puro
- **Canvas API**: Visualización de waveform
- **Audio API**: Reproducción de audio

### Dependencias del Sistema

- **FFmpeg**: Requerido por MoviePy para codificación de video
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt-get install ffmpeg`
  - Windows: Descargar desde https://ffmpeg.org

### Fuentes

- **Helvetica**: Fuente principal (sistema o fallback en `fonts/`)
- Busqueda de fuentes:
  1. Sistema (macOS: `/System/Library/Fonts/`)
  2. Carpeta `fonts/` del proyecto
  3. Fallback a fuente del sistema

---

## 🐛 Problemas Conocidos y Debugging

### 1. Video no se genera

**Síntomas**:
- El proceso de generación se inicia pero nunca termina
- Error 500 en el endpoint `/api/generate`
- El archivo de video no aparece en `outputs/`

**Causas posibles**:
- FFmpeg no está instalado o no está en PATH
- Error en la generación de clips (fondo, vinilo, texto)
- Problemas de memoria con archivos grandes
- Conflictos entre `bitrate` y `-crf` en `write_videofile()`

**Debugging**:
```bash
# Verificar FFmpeg
ffmpeg -version

# Revisar logs del servidor
tail -f server.log

# Verificar que los archivos existen
ls -la uploads/
ls -la outputs/

# Revisar logs de Python
# Los logs están configurados con nivel INFO
# Buscar mensajes que empiezan con 🎬, ✅, ❌
```

**Soluciones**:
- ✅ **Arreglado**: Removido conflicto entre `bitrate` y `-crf`
- ✅ **Arreglado**: Validación explícita de que clips no sean `None`
- ✅ **Arreglado**: Logging extensivo en `generate_video()`

### 2. Reproductor de audio no funciona

**Síntomas**:
- El audio no se reproduce al hacer click en "Reproducir"
- Error 404 al intentar cargar el audio
- Mensaje de error en la consola del navegador

**Causas posibles**:
- El archivo de audio no existe en `uploads/`
- URL encoding incorrecto del `file_id`
- CORS issues (poco probable)
- El endpoint `/api/audio/{file_id}` no encuentra el archivo

**Debugging**:
```javascript
// En la consola del navegador
console.log('Audio file ID:', appState.audioFileId);
console.log('Audio URL:', audioElement.src);
console.log('Audio error:', audioElement.error);
console.log('Audio readyState:', audioElement.readyState);
```

```bash
# En el servidor, revisar logs
# Buscar mensajes que empiezan con 🔍 DEBUG get_audio
```

**Soluciones**:
- ✅ **Arreglado**: URL encoding con `encodeURIComponent()`
- ✅ **Arreglado**: Logging extensivo en endpoint de audio
- ✅ **Arreglado**: Validación de `readyState` antes de reproducir
- ✅ **Arreglado**: Manejo de errores con mensajes descriptivos

### 3. Advertencia de extensión al arrastrar archivo MP3

**Síntomas**:
- Alert mostrando que el archivo no es válido
- Aunque el archivo es MP3, se rechaza

**Causas posibles**:
- `file.type` está vacío (común en algunos sistemas)
- Validación solo por MIME type, no por extensión
- Archivos sin extensión en el nombre

**Debugging**:
```javascript
// En handleDrop(), revisar:
console.log('File type:', file.type);
console.log('File name:', file.name);
console.log('File extension:', fileExtension);
```

**Soluciones**:
- ✅ **Arreglado**: Validación mejorada que usa extensión como fallback
- ✅ **Arreglado**: Soporte para archivos sin tipo MIME detectado
- ✅ **Arreglado**: Lista de extensiones válidas explícita

### 4. Errores de compatibilidad de Pillow

**Síntomas**:
- `Image.Resampling.LANCZOS` no existe
- `Image.ANTIALIAS` deprecated
- Error al procesar imágenes

**Causas**:
- Pillow 10.1.0 removió `LANCZOS` y `ANTIALIAS`
- Código usa constantes deprecadas

**Soluciones**:
- ✅ **Arreglado**: Reemplazado `LANCZOS` por `BICUBIC`
- ✅ **Arreglado**: Evitado uso de `Image.ANTIALIAS` en MoviePy

### 5. Errores de broadcasting en NumPy

**Síntomas**:
- `operands could not be broadcast together with shapes (800,800,3) (800,800,4)`
- Error al compositar video

**Causas**:
- Fondo animado genera RGB (3 canales)
- Vinilo genera RGBA (4 canales)
- MoviePy no puede combinar canales diferentes

**Soluciones**:
- ✅ **Arreglado**: Separación explícita de RGB y alpha
- ✅ **Arreglado**: Uso de máscaras en lugar de canales alpha directos

### 6. Problemas de font loading

**Síntomas**:
- Texto no se renderiza correctamente
- Error al cargar fuente Helvetica
- Fallback a fuente genérica

**Causas**:
- Helvetica no está disponible en el sistema
- Archivos `.ttc` requieren índice específico
- Ruta de fuentes incorrecta

**Soluciones**:
- ✅ **Implementado**: Búsqueda múltiple de fuentes (sistema → proyecto → fallback)
- ✅ **Implementado**: Soporte para archivos `.ttc` con índices
- ✅ **Implementado**: Fallback a fuentes del sistema

---

## 🔧 Guía de Desarrollo

### Iniciar el Servidor

```bash
# Activar entorno virtual
source venv/bin/activate  # macOS/Linux
# o
venv\Scripts\activate     # Windows

# Iniciar servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# O usar el script
./start.sh  # macOS/Linux
start.bat   # Windows
```

### Estructura de Logging

El proyecto usa logging de Python con nivel INFO. Los mensajes incluyen emojis para fácil identificación:

- 🎬 Inicio de generación de video
- ✅ Operación exitosa
- ❌ Error
- 🔍 Debug
- 📁 Operación de archivos
- 🗑️ Limpieza de archivos

### Testing Manual

1. **Subir archivo de audio**:
   - Arrastrar archivo MP3 a la zona de upload
   - Verificar que se extrae metadata correctamente
   - Verificar que se muestra waveform

2. **Reproducir audio**:
   - Hacer click en "Reproducir"
   - Verificar que el audio se reproduce
   - Cambiar selección y verificar que se actualiza

3. **Generar video**:
   - Configurar artista, título, tiempos
   - Hacer click en "Generar Video"
   - Verificar logs del servidor
   - Esperar a que se complete (puede tardar varios minutos)
   - Verificar que el video se descarga correctamente

### Debugging en el Navegador

Abrir las DevTools (F12) y revisar:

1. **Console**: Logs de JavaScript con prefijo 🔍 DEBUG
2. **Network**: Requests a la API, verificar status codes
3. **Application**: LocalStorage, verificar tokens si los hay

### Debugging en el Servidor

Revisar logs en tiempo real:

```bash
# Si se está usando uvicorn directamente
# Los logs aparecen en la terminal

# Si se está usando un archivo de log
tail -f server.log
```

### Manejo de Errores

El código tiene múltiples capas de manejo de errores:

1. **Frontend**: Try-catch en funciones async, validación de inputs
2. **Backend**: HTTPException para errores de API, logging de excepciones
3. **Services**: Validación de inputs, fallbacks para operaciones fallidas

### Optimizaciones Futuras

1. **Cache de waveforms**: Los waveforms se generan cada vez, podrían cachearse
2. **Procesamiento asíncrono**: Usar background tasks para generación de video
3. **Compresión de videos**: Reducir tamaño de archivos de salida
4. **Preview en tiempo real**: Mostrar preview del video antes de generar
5. **Progreso de generación**: WebSockets para actualizar progreso en tiempo real

---

## 📝 Notas Finales

### Limitaciones Actuales

- La generación de video es síncrona y puede tardar varios minutos
- No hay sistema de cola para procesar múltiples videos
- Los archivos temporales se acumulan en `uploads/` y `outputs/`
- No hay autenticación ni autorización
- No hay límite de tamaño de archivos subidos

### Mejoras Sugeridas

1. **Sistema de cola**: Usar Celery o similar para procesar videos en background
2. **Limpieza automática**: Eliminar archivos temporales después de un tiempo
3. **Autenticación**: Agregar sistema de usuarios
4. **Límites**: Validar tamaño de archivos y duración de videos
5. **Optimización**: Reducir tiempo de generación usando presets más rápidos
6. **Testing**: Agregar tests unitarios y de integración
7. **Documentación API**: Agregar OpenAPI/Swagger docs

---

## 🚀 Conclusión

DigVid es una aplicación funcional pero con margen de mejora. El código está bien estructurado y documentado, pero hay áreas donde se pueden hacer optimizaciones y mejoras de robustez. Los problemas conocidos están documentados y tienen soluciones implementadas o sugeridas.

Para futuras IAs trabajando en este proyecto, esta documentación proporciona un contexto completo de cómo funciona el sistema, dónde están los problemas, y cómo debuggearlos.

