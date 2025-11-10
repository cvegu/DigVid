import os
from typing import Optional, Tuple, List
from mutagen import File
from mutagen.id3 import ID3NoHeaderError
from PIL import Image
import io
import numpy as np
try:
    from moviepy.editor import AudioFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False


class AudioProcessor:
    """Procesador para extraer metadata y portada de archivos de audio."""
    
    SUPPORTED_FORMATS = ['.mp3', '.wav', '.flac', '.m4a', '.ogg', '.mp4', '.aac']
    
    @staticmethod
    def is_supported_format(filename: str) -> bool:
        """Verifica si el formato del archivo es soportado."""
        ext = os.path.splitext(filename.lower())[1]
        return ext in AudioProcessor.SUPPORTED_FORMATS
    
    @staticmethod
    def extract_metadata(audio_path: str) -> dict:
        """
        Extrae metadata de un archivo de audio.
        
        Returns:
            dict con las siguientes keys:
            - artist: str o None
            - title: str o None
            - duration: float (segundos)
            - album: str o None
        """
        try:
            audio_file = File(audio_path)
            if audio_file is None:
                return {
                    'artist': None,
                    'title': None,
                    'duration': 0.0,
                    'album': None
                }
            
            # Obtener duración
            duration = 0.0
            if hasattr(audio_file, 'info') and hasattr(audio_file.info, 'length'):
                duration = float(audio_file.info.length)
            
            metadata = {
                'artist': None,
                'title': None,
                'duration': duration,
                'album': None
            }
            
            # Extraer metadata según el tipo de archivo
            if hasattr(audio_file, 'tags') and audio_file.tags is not None:
                tags = audio_file.tags
                
                # Para MP3 (ID3 tags)
                # Artist: TPE1 (Lead performer/soloist) o TPE2 (Band/orchestra/accompaniment)
                if 'TPE1' in tags:
                    try:
                        metadata['artist'] = str(tags['TPE1'][0])
                    except (IndexError, KeyError, TypeError):
                        pass
                elif 'TPE2' in tags:
                    try:
                        metadata['artist'] = str(tags['TPE2'][0])
                    except (IndexError, KeyError, TypeError):
                        pass
                
                # Title: TIT2
                if 'TIT2' in tags:
                    try:
                        metadata['title'] = str(tags['TIT2'][0])
                    except (IndexError, KeyError, TypeError):
                        pass
                
                # Album: TALB
                if 'TALB' in tags:
                    try:
                        metadata['album'] = str(tags['TALB'][0])
                    except (IndexError, KeyError, TypeError):
                        pass
                
                # Para formatos Vorbis (FLAC, OGG) y otros
                # Artist
                if metadata['artist'] is None:
                    for key in ['ARTIST', 'artist', 'ARTISTS', '©ART']:
                        if key in tags:
                            try:
                                metadata['artist'] = str(tags[key][0])
                                break
                            except (IndexError, KeyError, TypeError):
                                continue
                
                # Title
                if metadata['title'] is None:
                    for key in ['TITLE', 'title', '©nam', '©NAM']:
                        if key in tags:
                            try:
                                metadata['title'] = str(tags[key][0])
                                break
                            except (IndexError, KeyError, TypeError):
                                continue
                
                # Album
                if metadata['album'] is None:
                    for key in ['ALBUM', 'album', '©alb', '©ALB']:
                        if key in tags:
                            try:
                                metadata['album'] = str(tags[key][0])
                                break
                            except (IndexError, KeyError, TypeError):
                                continue
            
            # Limpiar valores (remover espacios en blanco)
            if metadata['artist']:
                metadata['artist'] = metadata['artist'].strip()
            if metadata['title']:
                metadata['title'] = metadata['title'].strip()
            if metadata['album']:
                metadata['album'] = metadata['album'].strip()
            
            return metadata
            
        except Exception as e:
            print(f"Error extrayendo metadata: {e}")
            import traceback
            traceback.print_exc()
            return {
                'artist': None,
                'title': None,
                'duration': 0.0,
                'album': None
            }
    
    @staticmethod
    def extract_cover(audio_path: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Extrae la portada del archivo de audio.
        
        Args:
            audio_path: Ruta del archivo de audio
            output_path: Ruta donde guardar la portada (opcional)
        
        Returns:
            Ruta de la portada extraída o None si no se encuentra
        """
        try:
            audio_file = File(audio_path)
            if audio_file is None:
                return None
            
            cover_data = None
            cover_mime = None
            
            # Para MP3 con ID3v2 tags
            if hasattr(audio_file, 'tags') and audio_file.tags is not None:
                # Buscar APIC (Attached Picture) en ID3v2
                for tag_key in list(audio_file.tags.keys()):
                    if 'APIC' in tag_key or tag_key.startswith('APIC:'):
                        try:
                            apic = audio_file.tags[tag_key]
                            if hasattr(apic, 'data'):
                                cover_data = apic.data
                                if hasattr(apic, 'mime'):
                                    cover_mime = apic.mime
                                break
                        except (AttributeError, KeyError, IndexError, TypeError) as e:
                            continue
                    
                    # También buscar en tags genéricos
                    if 'PICTURE' in tag_key.upper() or 'COVER' in tag_key.upper():
                        try:
                            pic_tag = audio_file.tags[tag_key]
                            if hasattr(pic_tag, 'data'):
                                cover_data = pic_tag.data
                                break
                            elif isinstance(pic_tag, list) and len(pic_tag) > 0:
                                if hasattr(pic_tag[0], 'data'):
                                    cover_data = pic_tag[0].data
                                    break
                        except (AttributeError, KeyError, IndexError, TypeError):
                            continue
            
            # Para formatos Vorbis (FLAC, OGG) - usar pictures
            if cover_data is None:
                if hasattr(audio_file, 'pictures') and len(audio_file.pictures) > 0:
                    try:
                        # Tomar la primera imagen (generalmente la portada)
                        picture = audio_file.pictures[0]
                        if hasattr(picture, 'data'):
                            cover_data = picture.data
                            if hasattr(picture, 'mime'):
                                cover_mime = picture.mime
                    except (AttributeError, IndexError, TypeError):
                        pass
            
            # Para MP4/M4A - buscar en tags
            if cover_data is None and hasattr(audio_file, 'tags') and audio_file.tags is not None:
                # MP4 usa 'covr' tag
                if 'covr' in audio_file.tags:
                    try:
                        covr = audio_file.tags['covr']
                        if isinstance(covr, list) and len(covr) > 0:
                            cover_data = covr[0]
                    except (AttributeError, IndexError, TypeError):
                        pass
            
            if cover_data:
                try:
                    # Convertir bytes a imagen
                    if isinstance(cover_data, bytes):
                        image = Image.open(io.BytesIO(cover_data))
                    else:
                        # Algunos formatos devuelven la imagen directamente
                        image = cover_data
                        if not isinstance(image, Image.Image):
                            image = Image.open(io.BytesIO(image))
                    
                    # Convertir a RGB si es necesario
                    if image.mode in ('RGBA', 'LA', 'P'):
                        # Crear fondo blanco para imágenes transparentes
                        rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                        if image.mode == 'P':
                            image = image.convert('RGBA')
                        rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                        image = rgb_image
                    elif image.mode != 'RGB':
                        image = image.convert('RGB')
                    
                    # Si no se especifica output_path, crear uno temporal
                    if output_path is None:
                        base_name = os.path.splitext(os.path.basename(audio_path))[0]
                        output_dir = os.path.dirname(audio_path) or '.'
                        output_path = os.path.join(
                            output_dir,
                            f"{base_name}_cover.jpg"
                        )
                    
                    # Asegurar que el directorio existe
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    # Guardar imagen
                    image.save(output_path, 'JPEG', quality=95)
                    return output_path
                    
                except Exception as e:
                    print(f"Error procesando imagen de portada: {e}")
                    return None
            
            return None
            
        except Exception as e:
            print(f"Error extrayendo portada: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def generate_waveform(audio_path: str, width: int = 800, height: int = 200) -> Optional[List[float]]:
        """
        Genera datos de waveform para visualización.
        
        Args:
            audio_path: Ruta del archivo de audio
            width: Ancho del waveform (número de puntos)
            height: Alto del waveform (no usado actualmente, para futuras mejoras)
        
        Returns:
            Lista de valores de amplitud normalizados (0-1) o None si hay error
        """
        if not MOVIEPY_AVAILABLE:
            print("⚠️ MoviePy no está disponible, no se puede generar waveform")
            return None
        
        try:
            # Cargar audio
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            
            # Obtener el array de audio
            audio_array = audio_clip.to_soundarray()
            
            # Si es estéreo, convertir a mono (promedio de ambos canales)
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            
            # Calcular el número de muestras por punto del waveform
            samples_per_point = max(1, len(audio_array) // width)
            
            # Crear array de waveform reducido
            waveform = []
            for i in range(width):
                start_idx = int(i * samples_per_point)
                end_idx = int(min((i + 1) * samples_per_point, len(audio_array)))
                
                if start_idx < len(audio_array):
                    # Tomar el valor absoluto máximo en este rango
                    segment = audio_array[start_idx:end_idx]
                    max_amplitude = np.max(np.abs(segment))
                    waveform.append(float(max_amplitude))
                else:
                    waveform.append(0.0)
            
            # Normalizar waveform a rango [0, 1]
            if len(waveform) > 0:
                max_val = max(waveform)
                if max_val > 0:
                    waveform = [w / max_val for w in waveform]
            
            # Cerrar clip
            audio_clip.close()
            
            return waveform
            
        except Exception as e:
            print(f"Error generando waveform: {e}")
            import traceback
            traceback.print_exc()
            return None

