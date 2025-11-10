import os
import uuid
import re
import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import shutil
from pathlib import Path
import zipfile
import tempfile
from starlette.background import BackgroundTask

from app.services.audio_processor import AudioProcessor
from app.services.image_processor import ImageProcessor
from app.services.video_generator import VideoGenerator

router = APIRouter()

# Directorios
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


class GenerateVideoRequest(BaseModel):
    audio_file_id: str
    artist: str
    title: str
    start_time: float
    end_time: float
    cover_file_id: Optional[str] = None


class BatchSongItem(BaseModel):
    audio_file_id: str
    artist: str
    title: str
    start_time: float
    end_time: float
    cover_file_id: Optional[str] = None


class BatchGenerateRequest(BaseModel):
    songs: List[BatchSongItem]
    folder_name: str
    start_time: float  # Tiempo por defecto para todas las canciones
    end_time: float    # Tiempo por defecto para todas las canciones


@router.post("/upload/audio")
async def upload_audio(file: UploadFile = File(...)):
    """Sube un archivo de audio y extrae su metadata."""
    try:
        # Verificar formato
        if not AudioProcessor.is_supported_format(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Formato no soportado. Formatos soportados: {', '.join(AudioProcessor.SUPPORTED_FORMATS)}"
            )
        
        # Generar ID único para el archivo
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1]
        file_path = UPLOAD_DIR / f"{file_id}{file_ext}"
        
        # Guardar archivo
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extraer metadata
        metadata = AudioProcessor.extract_metadata(str(file_path))
        
        # Intentar extraer portada
        cover_path = AudioProcessor.extract_cover(str(file_path))
        cover_file_id = None
        if cover_path and os.path.exists(cover_path):
            cover_file_id = str(uuid.uuid4())
            cover_ext = os.path.splitext(cover_path)[1] or '.jpg'
            new_cover_path = UPLOAD_DIR / f"{cover_file_id}{cover_ext}"
            # Mover o copiar la portada al directorio de uploads
            try:
                if os.path.dirname(cover_path) != str(UPLOAD_DIR):
                    shutil.move(cover_path, new_cover_path)
                else:
                    # Si ya está en uploads, solo renombrar
                    os.rename(cover_path, new_cover_path)
                cover_file_id = f"{cover_file_id}{cover_ext}"
            except Exception as e:
                print(f"Error moviendo portada: {e}")
                # Si falla, intentar copiar
                try:
                    shutil.copy2(cover_path, new_cover_path)
                    cover_file_id = f"{cover_file_id}{cover_ext}"
                    # Eliminar el archivo original si es temporal
                    if os.path.dirname(cover_path) == str(UPLOAD_DIR):
                        try:
                            os.remove(cover_path)
                        except:
                            pass
                except Exception as e2:
                    print(f"Error copiando portada: {e2}")
                    cover_file_id = None
        
        return JSONResponse({
            "file_id": f"{file_id}{file_ext}",
            "filename": file.filename,
            "metadata": metadata,
            "cover_file_id": cover_file_id
        })
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error procesando archivo de audio: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error procesando archivo: {error_detail}")


@router.post("/upload/cover")
async def upload_cover(file: UploadFile = File(...)):
    """Sube una imagen de portada manualmente."""
    try:
        # Verificar que es una imagen
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
        
        # Generar ID único
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1] or '.jpg'
        file_path = UPLOAD_DIR / f"{file_id}{file_ext}"
        
        # Guardar archivo
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return JSONResponse({
            "cover_file_id": f"{file_id}{file_ext}"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error subiendo portada: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error subiendo portada: {error_detail}")


@router.post("/generate")
async def generate_video(request: GenerateVideoRequest):
    """Genera un video con los parámetros especificados."""
    processed_cover_path = None
    placeholder_cover_path = None
    output_path = None
    
    try:
        # Validar tiempos
        if request.start_time < 0 or request.end_time <= request.start_time:
            raise HTTPException(status_code=400, detail="Tiempos inválidos")
        
        # Encontrar archivo de audio
        audio_path = UPLOAD_DIR / request.audio_file_id
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Archivo de audio no encontrado")
        
        # Verificar duración del audio
        metadata = AudioProcessor.extract_metadata(str(audio_path))
        if request.end_time > metadata['duration']:
            raise HTTPException(
                status_code=400,
                detail=f"El tiempo final ({request.end_time}s) excede la duración del audio ({metadata['duration']:.2f}s)"
            )
        
        # Procesar portada
        try:
            if request.cover_file_id:
                cover_path = UPLOAD_DIR / request.cover_file_id
                if not cover_path.exists():
                    raise HTTPException(status_code=404, detail="Archivo de portada no encontrado")
            else:
                # Crear portada placeholder
                placeholder_cover_path = UPLOAD_DIR / f"placeholder_{uuid.uuid4()}.jpg"
                ImageProcessor.create_placeholder_cover(str(placeholder_cover_path))
                cover_path = placeholder_cover_path
            
            # Preparar portada (redimensionar y hacer circular)
            processed_cover_path = UPLOAD_DIR / f"processed_{uuid.uuid4()}.jpg"
            ImageProcessor.prepare_cover_image(str(cover_path), str(processed_cover_path))
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            print(f"Error procesando portada: {e}")
            traceback.print_exc()
            # Limpiar placeholder si se creó
            if placeholder_cover_path and placeholder_cover_path.exists():
                try:
                    os.remove(placeholder_cover_path)
                    placeholder_cover_path = None
                except:
                    pass
            raise HTTPException(status_code=500, detail=f"Error procesando portada: {str(e)}")
        
        # Generar video
        video_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{video_id}.mp4"
        
        try:
            generator = VideoGenerator()
            generator.generate_video(
                audio_path=str(audio_path),
                cover_path=str(processed_cover_path),
                output_path=str(output_path),
                artist=request.artist or "Unknown Artist",
                title=request.title or "Unknown Title",
                start_time=request.start_time,
                end_time=request.end_time
            )
            
            # Verificar que el video se generó correctamente
            if not output_path.exists():
                raise HTTPException(status_code=500, detail="El video no se generó correctamente")
            
        except Exception as e:
            import traceback
            error_detail = str(e)
            print(f"Error generando video: {e}")
            traceback.print_exc()
            # Limpiar archivos temporales en caso de error
            if processed_cover_path and processed_cover_path.exists():
                try:
                    os.remove(processed_cover_path)
                except:
                    pass
            if output_path and output_path.exists():
                try:
                    os.remove(output_path)
                except:
                    pass
            raise HTTPException(status_code=500, detail=f"Error generando video: {error_detail}")
        finally:
            # Limpiar portada procesada temporal
            if processed_cover_path and processed_cover_path.exists():
                try:
                    os.remove(processed_cover_path)
                except:
                    pass
            # Limpiar placeholder si se creó
            if placeholder_cover_path and placeholder_cover_path.exists():
                try:
                    os.remove(placeholder_cover_path)
                except:
                    pass
        
        return JSONResponse({
            "video_id": f"{video_id}.mp4",
            "message": "Video generado exitosamente"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error en generate_video: {e}")
        traceback.print_exc()
        # Limpiar archivos en caso de error no controlado
        if processed_cover_path and processed_cover_path.exists():
            try:
                os.remove(processed_cover_path)
            except:
                pass
        if placeholder_cover_path and placeholder_cover_path.exists():
            try:
                os.remove(placeholder_cover_path)
            except:
                pass
        if output_path and output_path.exists():
            try:
                os.remove(output_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error generando video: {error_detail}")


@router.get("/download/{video_id}")
async def download_video(video_id: str):
    """Descarga un video generado."""
    video_path = OUTPUT_DIR / video_id
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=video_id
    )


@router.get("/cover/{cover_file_id}")
async def get_cover(cover_file_id: str):
    """Obtiene una imagen de portada subida."""
    cover_path = UPLOAD_DIR / cover_file_id
    if not cover_path.exists():
        raise HTTPException(status_code=404, detail="Portada no encontrada")
    
    # Determinar media type
    ext = os.path.splitext(cover_file_id)[1].lower()
    media_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    media_type = media_types.get(ext, 'image/jpeg')
    
    return FileResponse(
        path=str(cover_path),
        media_type=media_type
    )


@router.get("/audio/{audio_file_id}")
async def get_audio(audio_file_id: str):
    """Obtiene un archivo de audio subido para reproducción."""
    try:
        # Decodificar el nombre del archivo en caso de que tenga caracteres especiales
        from urllib.parse import unquote
        audio_file_id = unquote(audio_file_id)
        
        audio_path = UPLOAD_DIR / audio_file_id
        if not audio_path.exists():
            # Listar archivos disponibles para debugging (solo en desarrollo)
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Audio file not found: {audio_file_id}")
            logger.error(f"Upload directory: {UPLOAD_DIR}")
            logger.error(f"Full path: {audio_path}")
            
            # Buscar archivos similares
            if UPLOAD_DIR.exists():
                files = list(UPLOAD_DIR.glob(f"*{os.path.splitext(audio_file_id)[1]}"))
                if files:
                    logger.error(f"Found similar files: {[f.name for f in files[:5]]}")
            
            raise HTTPException(status_code=404, detail=f"Archivo de audio no encontrado: {audio_file_id}")
        
        # Determinar media type
        ext = os.path.splitext(audio_file_id)[1].lower()
        media_types = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.flac': 'audio/flac',
            '.m4a': 'audio/mp4',
            '.ogg': 'audio/ogg',
            '.aac': 'audio/aac'
        }
        media_type = media_types.get(ext, 'audio/mpeg')
        
        return FileResponse(
            path=str(audio_path),
            media_type=media_type,
            filename=audio_file_id
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error sirviendo audio: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error sirviendo audio: {error_detail}")


@router.get("/metadata/{file_id}")
async def get_metadata(file_id: str):
    """Obtiene metadata de un archivo de audio subido."""
    audio_path = UPLOAD_DIR / file_id
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    metadata = AudioProcessor.extract_metadata(str(audio_path))
    return JSONResponse(metadata)


@router.get("/waveform/{file_id}")
async def get_waveform(file_id: str):
    """Obtiene datos de waveform de un archivo de audio para visualización."""
    try:
        audio_path = UPLOAD_DIR / file_id
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        waveform = AudioProcessor.generate_waveform(str(audio_path), width=800, height=200)
        
        if waveform is None:
            raise HTTPException(status_code=500, detail="Error generando waveform")
        
        return JSONResponse({
            "waveform": waveform,
            "points": len(waveform)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error obteniendo waveform: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error obteniendo waveform: {error_detail}")


@router.post("/batch/generate")
async def batch_generate_videos(request: BatchGenerateRequest):
    """Genera múltiples videos en lote."""
    try:
        # Validar que no haya más de 10 canciones
        if len(request.songs) > 10:
            raise HTTPException(status_code=400, detail="Máximo 10 canciones por lote")
        
        if len(request.songs) == 0:
            raise HTTPException(status_code=400, detail="Debe haber al menos una canción")
        
        # Crear carpeta de exportación con nombre personalizado
        # Limpiar el nombre de la carpeta para que sea válido en el sistema de archivos
        safe_folder_name = re.sub(r'[^\w\s-]', '', request.folder_name).strip()
        if not safe_folder_name:
            safe_folder_name = f"export_{uuid.uuid4().hex[:8]}"
        
        export_dir = OUTPUT_DIR / safe_folder_name
        export_dir.mkdir(exist_ok=True)
        
        # Lista para almacenar información de las canciones procesadas
        processed_songs = []
        errors = []
        
        # Procesar cada canción
        generator = VideoGenerator()
        
        for idx, song in enumerate(request.songs):
            try:
                # Validar tiempos (usar los de la canción o los por defecto)
                start_time = song.start_time if song.start_time >= 0 else request.start_time
                end_time = song.end_time if song.end_time > start_time else request.end_time
                
                if start_time < 0 or end_time <= start_time:
                    errors.append({
                        "song_index": idx,
                        "artist": song.artist,
                        "title": song.title,
                        "error": "Tiempos inválidos"
                    })
                    continue
                
                # Encontrar archivo de audio
                audio_path = UPLOAD_DIR / song.audio_file_id
                if not audio_path.exists():
                    errors.append({
                        "song_index": idx,
                        "artist": song.artist,
                        "title": song.title,
                        "error": "Archivo de audio no encontrado"
                    })
                    continue
                
                # Verificar duración del audio
                metadata = AudioProcessor.extract_metadata(str(audio_path))
                if end_time > metadata['duration']:
                    errors.append({
                        "song_index": idx,
                        "artist": song.artist,
                        "title": song.title,
                        "error": f"El tiempo final excede la duración del audio ({metadata['duration']:.2f}s)"
                    })
                    continue
                
                # Procesar portada
                processed_cover_path = None
                placeholder_cover_path = None
                try:
                    if song.cover_file_id:
                        cover_path = UPLOAD_DIR / song.cover_file_id
                        if not cover_path.exists():
                            raise HTTPException(status_code=404, detail="Archivo de portada no encontrado")
                    else:
                        # Crear portada placeholder
                        placeholder_cover_path = UPLOAD_DIR / f"placeholder_{uuid.uuid4()}.jpg"
                        ImageProcessor.create_placeholder_cover(str(placeholder_cover_path))
                        cover_path = placeholder_cover_path
                    
                    # Preparar portada (redimensionar y hacer circular)
                    processed_cover_path = UPLOAD_DIR / f"processed_{uuid.uuid4()}.jpg"
                    ImageProcessor.prepare_cover_image(str(cover_path), str(processed_cover_path))
                except Exception as e:
                    import traceback
                    print(f"Error procesando portada para {song.artist} - {song.title}: {e}")
                    traceback.print_exc()
                    if placeholder_cover_path and placeholder_cover_path.exists():
                        try:
                            os.remove(placeholder_cover_path)
                        except:
                            pass
                    errors.append({
                        "song_index": idx,
                        "artist": song.artist,
                        "title": song.title,
                        "error": f"Error procesando portada: {str(e)}"
                    })
                    continue
                
                # Generar video
                video_filename = f"{song.artist} - {song.title}.mp4"
                # Limpiar el nombre del archivo para que sea válido
                video_filename = re.sub(r'[<>:"/\\|?*]', '_', video_filename)
                output_path = export_dir / video_filename
                
                try:
                    generator.generate_video(
                        audio_path=str(audio_path),
                        cover_path=str(processed_cover_path),
                        output_path=str(output_path),
                        artist=song.artist or "Unknown Artist",
                        title=song.title or "Unknown Title",
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    # Verificar que el video se generó correctamente
                    if not output_path.exists():
                        errors.append({
                            "song_index": idx,
                            "artist": song.artist,
                            "title": song.title,
                            "error": "El video no se generó correctamente"
                        })
                    else:
                        processed_songs.append({
                            "artist": song.artist,
                            "title": song.title,
                            "filename": video_filename,
                            "status": "success"
                        })
                        
                except Exception as e:
                    import traceback
                    error_detail = str(e)
                    print(f"Error generando video para {song.artist} - {song.title}: {e}")
                    traceback.print_exc()
                    errors.append({
                        "song_index": idx,
                        "artist": song.artist,
                        "title": song.title,
                        "error": error_detail
                    })
                finally:
                    # Limpiar archivos temporales
                    if processed_cover_path and processed_cover_path.exists():
                        try:
                            os.remove(processed_cover_path)
                        except:
                            pass
                    if placeholder_cover_path and placeholder_cover_path.exists():
                        try:
                            os.remove(placeholder_cover_path)
                        except:
                            pass
                        
            except Exception as e:
                import traceback
                print(f"Error procesando canción {idx}: {e}")
                traceback.print_exc()
                errors.append({
                    "song_index": idx,
                    "artist": song.artist if hasattr(song, 'artist') else "Unknown",
                    "title": song.title if hasattr(song, 'title') else "Unknown",
                    "error": str(e)
                })
        
        # Generar archivo .txt con la lista de canciones
        list_file_path = export_dir / "lista_canciones.txt"
        with open(list_file_path, 'w', encoding='utf-8') as f:
            f.write(f"Lista de Canciones - {request.folder_name}\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Fecha de generación: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total de canciones: {len(request.songs)}\n")
            f.write(f"Procesadas exitosamente: {len(processed_songs)}\n")
            f.write(f"Errores: {len(errors)}\n\n")
            f.write("Canciones procesadas:\n")
            f.write("-" * 50 + "\n")
            for song in processed_songs:
                f.write(f"✓ {song['artist']} - {song['title']}\n")
                f.write(f"  Archivo: {song['filename']}\n\n")
            
            if errors:
                f.write("\nErrores:\n")
                f.write("-" * 50 + "\n")
                for error in errors:
                    f.write(f"✗ {error.get('artist', 'Unknown')} - {error.get('title', 'Unknown')}\n")
                    f.write(f"  Error: {error.get('error', 'Desconocido')}\n\n")
        
        return JSONResponse({
            "folder_name": safe_folder_name,
            "folder_path": str(export_dir),
            "processed": len(processed_songs),
            "errors": len(errors),
            "total": len(request.songs),
            "processed_songs": processed_songs,
            "errors_list": errors,
            "list_file": f"{safe_folder_name}/lista_canciones.txt"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error en batch_generate_videos: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generando videos en lote: {error_detail}")


@router.get("/batch/list")
async def list_batch_folders():
    """Lista todas las carpetas de exportación."""
    try:
        folders = []
        if OUTPUT_DIR.exists():
            for folder in OUTPUT_DIR.iterdir():
                if folder.is_dir():
                    # Contar archivos de video en la carpeta
                    video_files = list(folder.glob("*.mp4"))
                    list_file = folder / "lista_canciones.txt"
                    folders.append({
                        "name": folder.name,
                        "video_count": len(video_files),
                        "has_list": list_file.exists(),
                        "path": str(folder)
                    })
        return JSONResponse({"folders": folders})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listando carpetas: {str(e)}")


@router.get("/batch/download/{folder_name}/{filename}")
async def download_batch_video(folder_name: str, filename: str):
    """Descarga un video de una carpeta de lote."""
    # Validar nombre de carpeta para seguridad
    safe_folder_name = re.sub(r'[^\w\s-]', '', folder_name).strip()
    safe_filename = re.sub(r'[^\w\s.-]', '', filename).strip()
    
    video_path = OUTPUT_DIR / safe_folder_name / safe_filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=safe_filename
    )


@router.get("/batch/download-zip/{folder_name}")
async def download_batch_zip(folder_name: str):
    """Descarga toda la carpeta como ZIP."""
    try:
        # Validar nombre de carpeta
        safe_folder_name = re.sub(r'[^\w\s-]', '', folder_name).strip()
        
        folder_path = OUTPUT_DIR / safe_folder_name
        if not folder_path.exists() or not folder_path.is_dir():
            raise HTTPException(status_code=404, detail="Carpeta no encontrada")
        
        # Crear archivo ZIP temporal
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_zip_path = temp_zip.name
        temp_zip.close()
        
        # Crear ZIP
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in folder_path.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(folder_path)
                    zipf.write(file_path, arcname)
        
        # Función para limpiar el archivo temporal después de la descarga
        def cleanup_temp_file():
            try:
                if os.path.exists(temp_zip_path):
                    os.remove(temp_zip_path)
            except:
                pass
        
        return FileResponse(
            path=temp_zip_path,
            media_type="application/zip",
            filename=f"{safe_folder_name}.zip",
            background=BackgroundTask(cleanup_temp_file)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando ZIP: {str(e)}")

