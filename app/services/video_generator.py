import os
import uuid
import numpy as np
import math
import tempfile
from pathlib import Path
from moviepy.editor import (
    AudioFileClip, ImageClip, CompositeVideoClip, 
    TextClip, ColorClip, VideoClip
)
from PIL import Image, ImageDraw, ImageFont


class VideoGenerator:
    """Generador de videos con fondo animado, portada girando y texto."""
    
    VIDEO_WIDTH = 1080
    VIDEO_HEIGHT = 1350
    VINYL_SIZE = 800
    FPS = 30  # Aumentado para mejor calidad de animación
    # Calidad de renderizado (más alto = mejor calidad, más lento)
    RENDER_QUALITY = 'high'  # 'high' para mejor anti-aliasing
    
    # Ruta de la carpeta de fuentes (relativa al directorio del proyecto)
    FONTS_DIR = Path("fonts")
    
    # Nombre de la fuente por defecto (sin extensión)
    DEFAULT_FONT_NAME = "Helvetica"
    
    def __init__(self):
        # Verificar que FFmpeg está instalado (MoviePy lo verificará automáticamente al usarlo)
        pass
    
    @staticmethod
    def find_font_file(font_name: str = None, font_size: int = 60):
        """
        Busca un archivo de fuente en la carpeta fonts/ o en el sistema.
        PRIORIDAD: Intenta cargar por nombre del sistema primero (macOS).
        
        Args:
            font_name: Nombre de la fuente (sin extensión). Si es None, usa DEFAULT_FONT_NAME
            font_size: Tamaño de la fuente
        
        Returns:
            ImageFont: Objeto de fuente de PIL, o None si no se encuentra
        """
        if font_name is None:
            font_name = VideoGenerator.DEFAULT_FONT_NAME
        
        # PRIORIDAD 1: Intentar cargar directamente por nombre del sistema (macOS)
        # Esto funciona mejor en macOS donde las fuentes están registradas
        try:
            import platform
            if platform.system() == 'Darwin':  # macOS
                # Para Helvetica, intentar cargar directamente
                if font_name.lower() in ['helvetica', 'helvetica neue']:
                    try:
                        # Intentar cargar Helvetica directamente (funciona en macOS)
                        return ImageFont.truetype("Helvetica", font_size)
                    except:
                        try:
                            return ImageFont.truetype("Helvetica Neue", font_size)
                        except:
                            pass
        except:
            pass
        
        # PRIORIDAD 2: Buscar Helvetica específicamente en macOS (con index para .ttc)
        if font_name.lower() in ['helvetica', 'helvetica neue', 'helvetica-bold', 'helvetica neue bold']:
            helvetica_paths = [
                ("/System/Library/Fonts/Helvetica.ttc", 0),
                ("/System/Library/Fonts/HelveticaNeue.ttc", 0),
                ("/System/Library/Fonts/Supplemental/Helvetica.ttc", 0),
            ]
            # Para bold, intentar diferentes índices
            if 'bold' in font_name.lower():
                indices_to_try = [1, 2, 3, 4, 5, 0]
            else:
                indices_to_try = [0, 1, 2, 3, 4, 5]
            
            for font_path, _ in helvetica_paths:
                if os.path.exists(font_path):
                    for index in indices_to_try:
                        try:
                            return ImageFont.truetype(font_path, font_size, index=index)
                        except:
                            try:
                                # Intentar sin índice
                                return ImageFont.truetype(font_path, font_size)
                            except:
                                continue
        
        # PRIORIDAD 3: Buscar en la carpeta fonts/ del proyecto
        fonts_dir = VideoGenerator.FONTS_DIR
        if fonts_dir.exists():
            font_extensions = ['.ttf', '.otf', '.ttc']
            for ext in font_extensions:
                # Buscar exactamente el nombre
                font_path = fonts_dir / f"{font_name}{ext}"
                if font_path.exists():
                    try:
                        return ImageFont.truetype(str(font_path), font_size)
                    except Exception as e:
                        continue
                
                # Buscar variantes comunes (Bold, Regular, etc.)
                for variant in ['', '-Bold', '-Regular', '-Light', '-Medium', '-Heavy']:
                    font_path = fonts_dir / f"{font_name}{variant}{ext}"
                    if font_path.exists():
                        try:
                            return ImageFont.truetype(str(font_path), font_size)
                        except Exception as e:
                            continue
        
        # PRIORIDAD 4: Buscar en el sistema (macOS)
        system_font_paths = [
            f"/System/Library/Fonts/{font_name}.ttc",
            f"/System/Library/Fonts/{font_name}.ttf",
            f"/System/Library/Fonts/Supplemental/{font_name}.ttf",
            f"/Library/Fonts/{font_name}.ttf",
            f"~/Library/Fonts/{font_name}.ttf",
        ]
        
        for font_path in system_font_paths:
            expanded_path = os.path.expanduser(font_path)
            if os.path.exists(expanded_path):
                try:
                    return ImageFont.truetype(expanded_path, font_size)
                except Exception as e:
                    continue
        
        # Fallback: fuente por defecto
        print(f"⚠️ No se encontró la fuente '{font_name}', usando fuente por defecto")
        return ImageFont.load_default()
    
    @staticmethod
    def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
        """
        Divide el texto en líneas que caben en el ancho máximo sin cortar palabras.
        
        Args:
            text: Texto a dividir
            font: Fuente para medir el texto
            max_width: Ancho máximo en píxeles
        
        Returns:
            list: Lista de líneas de texto
        """
        if not text:
            return []
        
        words = text.split()
        if not words:
            return []
        
        lines = []
        current_line = []
        
        # Crear un draw temporal para medir texto
        temp_img = Image.new('RGB', (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        
        for word in words:
            # Probar agregar la palabra a la línea actual
            test_line = ' '.join(current_line + [word])
            bbox = temp_draw.textbbox((0, 0), test_line, font=font)
            test_width = bbox[2] - bbox[0]
            
            if test_width <= max_width:
                # La palabra cabe, agregarla
                current_line.append(word)
            else:
                # La palabra no cabe
                if current_line:
                    # Guardar la línea actual y empezar una nueva
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # La palabra sola es más ancha que max_width
                    # Forzar que quepa reduciendo el tamaño (esto no debería pasar normalmente)
                    lines.append(word)
                    current_line = []
        
        # Agregar la última línea si hay algo
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    @staticmethod
    def get_font_path_for_moviepy(font_name: str = None):
        """
        Obtiene la ruta de la fuente para usar con MoviePy TextClip.
        
        Args:
            font_name: Nombre de la fuente (sin extensión)
        
        Returns:
            str: Ruta de la fuente, o None si no se encuentra
        """
        if font_name is None:
            font_name = VideoGenerator.DEFAULT_FONT_NAME
        
        # Extensiones de fuentes soportadas
        font_extensions = ['.ttf', '.otf', '.ttc']
        
        # 1. Buscar en la carpeta fonts/ del proyecto
        fonts_dir = VideoGenerator.FONTS_DIR
        if fonts_dir.exists():
            for ext in font_extensions:
                font_path = fonts_dir / f"{font_name}{ext}"
                if font_path.exists():
                    return str(font_path.resolve())
                
                # Buscar variantes
                for variant in ['', '-Bold', '-Regular', '-Light', '-Medium', '-Heavy']:
                    font_path = fonts_dir / f"{font_name}{variant}{ext}"
                    if font_path.exists():
                        return str(font_path.resolve())
        
        # 2. Buscar en el sistema
        system_font_paths = [
            f"/System/Library/Fonts/{font_name}.ttc",
            f"/System/Library/Fonts/{font_name}.ttf",
            f"/System/Library/Fonts/Supplemental/{font_name}.ttf",
        ]
        
        for font_path in system_font_paths:
            if os.path.exists(font_path):
                return font_path
        
        # 3. Helvetica específico
        if font_name.lower() in ['helvetica', 'helvetica neue']:
            helvetica_paths = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/HelveticaNeue.ttc",
            ]
            for font_path in helvetica_paths:
                if os.path.exists(font_path):
                    return font_path
        
        return None
    
    @staticmethod
    def extract_dominant_colors(cover_path: str, num_colors: int = 4) -> list:
        """
        Extrae colores dominantes de la portada.
        
        Args:
            cover_path: Ruta de la imagen de portada
            num_colors: Número de colores a extraer
        
        Returns:
            Lista de colores RGB [r, g, b]
        """
        try:
            from PIL import Image
            import numpy as np
            
            # Cargar imagen
            img = Image.open(cover_path)
            # Redimensionar para acelerar el procesamiento
            img = img.resize((150, 150), Image.Resampling.BICUBIC)
            
            # Convertir a numpy array
            img_array = np.array(img)
            
            # Si tiene canal alpha, descartarlo
            if img_array.shape[2] == 4:
                img_array = img_array[:, :, :3]
            
            # Aplanar la imagen
            pixels = img_array.reshape(-1, 3)
            
            # Usar k-means simple para encontrar colores dominantes
            # Método simplificado: usar cuantización de colores
            # Reducir a menos colores únicos y encontrar los más comunes
            from collections import Counter
            
            # Reducir precisión de colores (agrupar colores similares)
            pixels_quantized = (pixels // 32) * 32  # Reducir a 8 niveles por canal
            
            # Contar colores más comunes
            color_counts = Counter(tuple(p) for p in pixels_quantized)
            dominant_colors_tuples = color_counts.most_common(num_colors)
            
            # Convertir a arrays numpy
            dominant_colors = []
            for color_tuple, count in dominant_colors_tuples:
                # Asegurar que no sea demasiado claro ni demasiado oscuro
                brightness = sum(color_tuple) / 3
                if 30 < brightness < 220:  # Filtrar colores muy oscuros o muy claros
                    dominant_colors.append(np.array(color_tuple, dtype=np.float32))
            
            # Si no hay suficientes colores válidos, generar variaciones
            if len(dominant_colors) < num_colors:
                if len(dominant_colors) > 0:
                    base_color = dominant_colors[0]
                    # Crear variaciones del color base
                    while len(dominant_colors) < num_colors:
                        # Variar el color base (más oscuro, más claro, más saturado)
                        variation_factor = 0.7 + (len(dominant_colors) * 0.1)
                        new_color = base_color * variation_factor
                        new_color = np.clip(new_color, 20, 200)
                        dominant_colors.append(new_color)
                else:
                    # Fallback: usar colores por defecto
                    dominant_colors = [
                        np.array([30, 30, 60], dtype=np.float32),
                        np.array([60, 40, 100], dtype=np.float32),
                        np.array([40, 60, 120], dtype=np.float32),
                        np.array([80, 50, 130], dtype=np.float32)
                    ]
            
            # Asegurar que tenemos exactamente num_colors
            while len(dominant_colors) < num_colors:
                dominant_colors.append(dominant_colors[-1])
            
            # Oscurecer ligeramente los colores para el fondo (para mejor contraste)
            dominant_colors = [np.clip(color * 0.6, 20, 180) for color in dominant_colors[:num_colors]]
            
            return dominant_colors
            
        except Exception as e:
            print(f"Error extrayendo colores dominantes: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: colores por defecto
            return [
                np.array([30, 30, 60], dtype=np.float32),
                np.array([60, 40, 100], dtype=np.float32),
                np.array([40, 60, 120], dtype=np.float32),
                np.array([80, 50, 130], dtype=np.float32)
            ]
    
    def create_animated_background(self, duration: float, cover_path: str = None, width: int = VIDEO_WIDTH, height: int = VIDEO_HEIGHT):
        """
        Crea un fondo animado con efecto tipo "liquid glass" basado en colores de la portada.
        Usa gradientes animados con movimiento suave (vectorizado para mejor rendimiento).
        
        Args:
            duration: Duración del fondo
            cover_path: Ruta de la portada para extraer colores (opcional)
            width: Ancho del video
            height: Alto del video
        """
        # Extraer colores dominantes de la portada si está disponible
        if cover_path and os.path.exists(cover_path):
            dominant_colors = self.extract_dominant_colors(cover_path, num_colors=4)
            color1 = dominant_colors[0] if len(dominant_colors) > 0 else np.array([30, 30, 60], dtype=np.float32)
            color2 = dominant_colors[1] if len(dominant_colors) > 1 else np.array([60, 40, 100], dtype=np.float32)
            color3 = dominant_colors[2] if len(dominant_colors) > 2 else np.array([40, 60, 120], dtype=np.float32)
            color4 = dominant_colors[3] if len(dominant_colors) > 3 else np.array([80, 50, 130], dtype=np.float32)
        else:
            # Colores por defecto si no hay portada
            color1 = np.array([30, 30, 60], dtype=np.float32)   # Azul oscuro
            color2 = np.array([60, 40, 100], dtype=np.float32)  # Púrpura
            color3 = np.array([40, 60, 120], dtype=np.float32)  # Azul medio
            color4 = np.array([80, 50, 130], dtype=np.float32)  # Púrpura claro
        
        def make_frame(t):
            
            # Animación basada en tiempo
            time_factor = t * 0.3  # Velocidad de animación
            
            # Crear coordenadas
            y_coords, x_coords = np.ogrid[0:height, 0:width]
            center_x, center_y = width // 2, height // 2
            
            # Distancias y ángulos (vectorizado)
            dx = x_coords - center_x
            dy = y_coords - center_y
            dist = np.sqrt(dx**2 + dy**2)
            angle = np.arctan2(dy, dx) + time_factor
            max_dist = math.sqrt(center_x**2 + center_y**2)
            
            # Crear ondas para efecto líquido
            wave1 = np.sin(angle * 2 + dist * 0.008 + time_factor * 1.5) * 0.5 + 0.5
            wave2 = np.sin(angle * 3.5 + dist * 0.012 + time_factor * 2.2) * 0.5 + 0.5
            wave = (wave1 + wave2) / 2
            
            # Factor de distancia normalizado
            dist_factor = np.clip(dist / max_dist, 0, 1.0)
            
            # Crear gradiente radial con animación
            radial = dist_factor + wave * 0.4 + time_factor * 0.05
            radial = np.clip(radial, 0, 1)
            
            # Interpolar entre colores basado en posición radial usando interpolación suave continua
            # Crear frame RGB
            frame = np.zeros((height, width, 3), dtype=np.float32)
            
            # Normalizar radial a rango [0, 1] con suavizado para evitar discontinuidades
            radial_normalized = np.clip(radial, 0, 1)
            
            # Usar interpolación cúbica suave para transiciones sin discontinuidades
            # Crear puntos de control para la interpolación
            control_points = np.array([
                [0.0, 0.0],      # color1 en 0.0
                [0.3, 0.3],      # color2 en 0.3
                [0.6, 0.6],      # color3 en 0.6
                [0.85, 0.85],    # color4 en 0.85
                [1.0, 1.0]       # color4 en 1.0
            ])
            
            # Interpolación suave usando np.interp para cada canal de color
            # Esto evita las discontinuidades de las zonas
            for i in range(3):
                # Crear valores de color en los puntos de control
                color_values = np.array([
                    color1[i],
                    color2[i],
                    color3[i],
                    color4[i],
                    color4[i]
                ])
                
                # Interpolar suavemente usando np.interp
                frame[:, :, i] = np.interp(radial_normalized, control_points[:, 0], color_values)
            
            # Aplicar efecto de brillo variable (liquid glass) con suavizado
            brightness = 0.75 + wave * 0.25
            frame = frame * np.expand_dims(brightness, axis=2)
            
            # La interpolación continua con np.interp ya elimina las discontinuidades
            # No necesitamos suavizado adicional que ralentiza el proceso
            # El gradiente radial suave con interpolación continua es suficiente
            
            # Convertir a uint8 y asegurar límites
            frame = np.clip(frame, 0, 255).astype(np.uint8)
            
            # Aplicar blur gaussiano suave para eliminar líneas de discontinuidad
            # Usar scipy si está disponible, sino usar filtro simple de numpy
            try:
                from scipy.ndimage import gaussian_filter
                # Blur muy suave (sigma=0.8) para eliminar líneas sin perder detalle
                frame = gaussian_filter(frame.astype(np.float32), sigma=(0.8, 0.8, 0))
                frame = np.clip(frame, 0, 255).astype(np.uint8)
            except ImportError:
                # Fallback: usar un filtro de promedio simple si scipy no está disponible
                # Crear kernel de blur simple 3x3
                kernel = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]], dtype=np.float32) / 16.0
                # Aplicar blur a cada canal
                for c in range(3):
                    channel = frame[:, :, c].astype(np.float32)
                    # Aplicar convolución simple (solo para píxeles internos)
                    blurred = np.zeros_like(channel)
                    for i in range(1, height-1):
                        for j in range(1, width-1):
                            blurred[i, j] = np.sum(channel[i-1:i+2, j-1:j+2] * kernel)
                    frame[:, :, c] = np.clip(blurred, 0, 255).astype(np.uint8)
            
            # Asegurar que el frame tiene 3 canales (RGB)
            if len(frame.shape) == 2:
                # Escala de grises, convertir a RGB
                frame = np.stack([frame, frame, frame], axis=2)
            elif frame.shape[2] == 1:
                # Un solo canal, convertir a RGB
                frame = np.repeat(frame, 3, axis=2)
            elif frame.shape[2] == 4:
                # RGBA, convertir a RGB (descartar alpha)
                frame = frame[:, :, :3]
            elif frame.shape[2] != 3:
                # Otro formato, tomar primeros 3 canales
                frame = frame[:, :, :3]
            
            return frame
        
        # Crear clip usando VideoClip con función personalizada
        clip = VideoClip(make_frame, duration=duration)
        clip = clip.set_fps(self.FPS)
        
        return clip
    
    def create_rotating_vinyl(self, cover_path: str, duration: float, size: int = VINYL_SIZE):
        """
        Crea un clip de la portada girando como un vinilo.
        
        Args:
            cover_path: Ruta de la imagen de portada
            duration: Duración del clip
            size: Tamaño del vinilo
        
        Returns:
            ImageClip: Clip de video con la portada rotando
        """
        temp_path = None
        try:
            # Cargar y preparar imagen
            img = Image.open(cover_path).convert('RGB')
            img = img.resize((size, size), Image.Resampling.BICUBIC)
            
            # Crear máscara circular
            mask = Image.new('L', (size, size), 0)
            draw = ImageDraw.Draw(mask)
            margin = 5
            draw.ellipse([margin, margin, size - margin, size - margin], fill=255)
            
            # Aplicar máscara a la imagen - convertir a RGBA primero
            img_rgba = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            img_rgba.paste(img, (0, 0))
            img_rgba.putalpha(mask)
            
            # Guardar imagen temporal con alpha usando UUID para evitar conflictos
            temp_dir = os.path.dirname(cover_path) or 'uploads'
            os.makedirs(temp_dir, exist_ok=True)
            temp_filename = f"masked_{uuid.uuid4()}_{os.path.basename(cover_path)}.png"
            temp_path = os.path.join(temp_dir, temp_filename)
            img_rgba.save(temp_path, 'PNG')
            
            # Cargar la imagen PNG que tiene canal alpha
            # Vamos a crear un VideoClip personalizado que maneje la rotación y la máscara correctamente
            rpm = 33.333
            rotations_per_second = rpm / 60.0
            
            # Cargar la imagen RGBA una vez
            pil_img_rgba = Image.open(temp_path).convert('RGBA')
            img_array_rgba = np.array(pil_img_rgba)

            def make_rotating_frame(t):
                # Calcular ángulo de rotación
                angle = (t * rotations_per_second * 360) % 360

                # Convertir array a PIL Image
                frame_img = Image.fromarray(img_array_rgba, 'RGBA')

                # Rotar manteniendo el tamaño con mejor calidad (BICUBIC para mejor anti-aliasing)
                rotated_img = frame_img.rotate(-angle, expand=False, resample=Image.Resampling.BICUBIC, fillcolor=(0, 0, 0, 0))

                # Convertir de vuelta a numpy array
                rotated_array = np.array(rotated_img)

                # Asegurar que tenemos RGBA
                if rotated_array.shape[2] != 4:
                    # Si no es RGBA, crear uno
                    if rotated_array.shape[2] == 3:
                        # RGB, agregar canal alpha opaco
                        alpha = np.ones((rotated_array.shape[0], rotated_array.shape[1], 1), dtype=np.uint8) * 255
                        rotated_array = np.concatenate([rotated_array, alpha], axis=2)
                    else:
                        # Formato desconocido, convertir a RGB primero
                        if len(rotated_array.shape) == 2:
                            rotated_array = np.stack([rotated_array, rotated_array, rotated_array], axis=2)
                        alpha = np.ones((rotated_array.shape[0], rotated_array.shape[1], 1), dtype=np.uint8) * 255
                        rotated_array = np.concatenate([rotated_array[:, :, :3], alpha], axis=2)

                # Separar RGB y alpha
                rgb_frame = rotated_array[:, :, :3].astype(np.uint8)
                alpha_mask = (rotated_array[:, :, 3] / 255.0).astype(np.float32)

                # Para MoviePy, cuando usamos has_mask, necesitamos devolver RGB
                # La máscara se maneja por separado
                return rgb_frame

            def make_mask_frame(t):
                # Calcular ángulo de rotación (mismo que el frame)
                angle = (t * rotations_per_second * 360) % 360
                
                # Extraer canal alpha de la imagen original
                alpha_channel = img_array_rgba[:, :, 3]
                alpha_img = Image.fromarray(alpha_channel, 'L')

                # Rotar la máscara con mejor calidad
                rotated_alpha = alpha_img.rotate(-angle, expand=False, resample=Image.Resampling.BICUBIC, fillcolor=0)
                rotated_alpha_array = np.array(rotated_alpha)

                # Asegurar que es 2D (MoviePy espera máscara 2D)
                if len(rotated_alpha_array.shape) > 2:
                    rotated_alpha_array = rotated_alpha_array[:, :, 0]

                # Normalizar a 0-1 para la máscara de MoviePy (debe ser float entre 0 y 1)
                mask_normalized = (rotated_alpha_array.astype(np.float32) / 255.0)

                # Asegurar que está en el rango [0, 1]
                mask_normalized = np.clip(mask_normalized, 0.0, 1.0)

                return mask_normalized

            # Crear clip de video con rotación
            img_clip = VideoClip(make_rotating_frame, duration=duration)
            img_clip = img_clip.set_fps(self.FPS)

            # Crear máscara para transparencia
            mask_clip = VideoClip(make_mask_frame, duration=duration, ismask=True)
            mask_clip = mask_clip.set_fps(self.FPS)

            # Aplicar máscara al clip
            img_clip = img_clip.set_mask(mask_clip)
            
            # Posicionar en el centro
            center_x = (self.VIDEO_WIDTH - size) // 2
            center_y = (self.VIDEO_HEIGHT - size) // 2
            img_clip = img_clip.set_position((center_x, center_y))
            
            # Almacenar la ruta temporal para limpieza
            img_clip._temp_mask_path = temp_path
            
            return img_clip
            
        except Exception as e:
            print(f"Error creando vinilo rotatorio: {e}")
            import traceback
            traceback.print_exc()
            # Limpiar archivo temporal si existe
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            # Fallback: crear un clip estático
            # Redimensionar la imagen antes de crear el clip para evitar usar resize() de MoviePy
            # (que usa Image.ANTIALIAS que no existe en Pillow 10+)
            try:
                fallback_img = Image.open(cover_path).convert('RGB')
                fallback_img = fallback_img.resize((size, size), Image.Resampling.BICUBIC)
                # Guardar temporalmente
                fallback_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                fallback_img.save(fallback_temp.name, 'JPEG')
                fallback_temp.close()
                
                img_clip = ImageClip(fallback_temp.name, duration=duration)
                center_x = (self.VIDEO_WIDTH - size) // 2
                center_y = (self.VIDEO_HEIGHT - size) // 2
                img_clip = img_clip.set_position((center_x, center_y))
                img_clip._temp_mask_path = fallback_temp.name  # Guardar para limpiar después
                return img_clip
            except Exception as e2:
                print(f"Error en fallback de vinilo: {e2}")
                import traceback
                traceback.print_exc()
                # Si falla el fallback, crear un clip simple sin redimensionar
                try:
                    img_clip = ImageClip(cover_path, duration=duration)
                    center_x = (self.VIDEO_WIDTH - size) // 2
                    center_y = (self.VIDEO_HEIGHT - size) // 2
                    img_clip = img_clip.set_position((center_x, center_y))
                    img_clip._temp_mask_path = None
                    return img_clip
                except Exception as e3:
                    print(f"Error crítico creando vinilo: {e3}")
                    # Último recurso: crear un clip de color sólido
                    raise
    
    
    def create_text_overlay(self, artist: str, title: str, duration: float):
        """
        Crea overlay de texto con artista (bold) y título (normal).
        
        Args:
            artist: Nombre del artista (se mostrará en bold)
            title: Título de la canción (se mostrará en normal)
            duration: Duración del clip
        
        Returns:
            tuple: (TextClip, list) - El clip de texto y lista de archivos temporales a limpiar
        """
        temp_files = []
        
        # Usar el método de búsqueda de fuentes
        font_size = 60
        # Buscar fuente normal y bold por separado - forzar Helvetica
        font_normal = VideoGenerator.find_font_file(font_name="Helvetica", font_size=font_size)
        # Si no se encuentra, intentar sin especificar nombre (usará DEFAULT_FONT_NAME)
        if font_normal is None or isinstance(font_normal, type(ImageFont.load_default())):
            font_normal = VideoGenerator.find_font_file(font_size=font_size)
        
        # Buscar Helvetica Bold
        font_bold = VideoGenerator.find_font_file(font_name="Helvetica-Bold", font_size=font_size)
        # Si no se encuentra bold, intentar con otras variantes
        if font_bold is None:
            # Intentar buscar bold de otra forma
            try:
                # Intentar cargar bold desde el sistema (macOS tiene Helvetica en .ttc)
                # Para .ttc, necesitamos cargar con índice diferente o buscar variantes
                font_bold_paths = [
                    "/System/Library/Fonts/Helvetica.ttc",  # Puede tener bold en índice diferente
                    "/System/Library/Fonts/HelveticaNeue.ttc",
                ]
                for path in font_bold_paths:
                    if os.path.exists(path):
                        try:
                            # Intentar diferentes índices para encontrar bold
                            for index in range(5):  # Probar primeros 5 índices
                                try:
                                    test_font = ImageFont.truetype(path, font_size, index=index)
                                    # Verificar si es bold comparando con normal
                                    if test_font != font_normal:
                                        font_bold = test_font
                                        break
                                except:
                                    continue
                            if font_bold:
                                break
                            # Si no encontramos por índice, intentar sin índice
                            try:
                                font_bold = ImageFont.truetype(path, font_size)
                                if font_bold != font_normal:
                                    break
                            except:
                                pass
                        except:
                            continue
            except Exception as e:
                print(f"Error buscando fuente bold: {e}")
        
        # Si aún no se encuentra bold, usar la fuente normal pero hacerla más gruesa
        if font_bold is None or font_bold == font_normal:
            # Usar la fuente normal y aplicar efecto de stroke más grueso para simular bold
            font_bold = font_normal
        
        font_path_for_moviepy = VideoGenerator.get_font_path_for_moviepy()
        
        # Para MoviePy TextClip, necesitamos texto combinado (pero mejor usar PIL para control de bold)
        # Intentar con TextClip primero, pero generalmente usaremos PIL para mejor control
        text_combined = f"{artist}\n{title}" if (artist and title) else (artist or title or "Unknown")
        
        try:
            # Intentar crear texto con TextClip (si ImageMagick está disponible)
            # Nota: TextClip tiene limitaciones para bold/normal, así que mejor usar PIL
            # Pero intentamos primero por si acaso
            if font_path_for_moviepy:
                txt_clip = TextClip(
                    text_combined,
                    fontsize=font_size,
                    color='white',
                    font=font_path_for_moviepy,
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(VideoGenerator.VIDEO_WIDTH - 100, None),
                    align='center'
                )
            else:
                    txt_clip = TextClip(
                    text_combined,
                    fontsize=font_size,
                        color='white',
                    stroke_color='black',
                    stroke_width=2,
                        method='caption',
                        size=(VideoGenerator.VIDEO_WIDTH - 100, None),
                        align='center'
                    )
            # Si TextClip funciona, saltamos al final
            txt_clip = txt_clip.set_duration(duration)
            txt_clip = txt_clip.set_position(('center', VideoGenerator.VIDEO_HEIGHT - 200))
            txt_clip._temp_files = []
            return txt_clip
        except Exception:
            # Fallback a PIL (que es mejor para control de bold/normal)
            pass
        
        # Siempre usar PIL para mejor control de artista (bold) y título (normal)
        # Primero calcular el tamaño necesario dinámicamente
        target_width = VideoGenerator.VIDEO_WIDTH - 100
        max_text_width = target_width - 40  # Margen de 20px a cada lado
        
        # Crear un draw temporal para medir texto
        temp_img = Image.new('RGB', (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        
        # Calcular altura necesaria
        total_height = 40  # Margen superior e inferior
        artist_lines = []
        title_lines = []
        test_font = font_normal  # Fuente para el título (puede cambiar si es muy largo)
        
        # Wrap texto del artista
        if artist and artist.strip():
            artist_text = artist.strip()
            artist_lines = VideoGenerator.wrap_text(artist_text, font_bold, max_text_width)
            # Calcular altura del artista
            for line in artist_lines:
                bbox = temp_draw.textbbox((0, 0), line, font=font_bold)
                total_height += (bbox[3] - bbox[1]) + 5  # Altura de línea + espaciado
            total_height += 15  # Espaciado después del artista
        
        # Wrap texto del título
        if title and title.strip():
            title_text = title.strip()
            # Si el título es muy largo, reducir tamaño de fuente
            test_size = font_size
            title_lines = VideoGenerator.wrap_text(title_text, font_normal, max_text_width)
            
            # Si el título necesita más de 2 líneas o es muy largo, reducir tamaño
            if len(title_lines) > 2 or (len(title_lines) == 2 and len(title_text) > 50):
                test_size = int(font_size * 0.85)  # Reducir 15%
                try:
                    # Intentar cargar fuente con tamaño reducido
                    test_font = VideoGenerator.find_font_file(font_name="Helvetica", font_size=test_size)
                    if test_font is None or isinstance(test_font, type(ImageFont.load_default())):
                        test_font = font_normal
                    title_lines = VideoGenerator.wrap_text(title_text, test_font, max_text_width)
                except Exception:
                    test_font = font_normal
            
            # Calcular altura del título
            for line in title_lines:
                bbox = temp_draw.textbbox((0, 0), line, font=test_font)
                total_height += (bbox[3] - bbox[1]) + 5  # Altura de línea + espaciado
        
        # Crear imagen de texto con altura dinámica
        target_height = max(250, total_height)  # Mínimo 250px
        txt_img = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(txt_img)
        
        y_offset = 20
        
        # Dibujar artista en BOLD (puede ser múltiples líneas)
        if artist_lines:
            for line in artist_lines:
                bbox_artist = draw.textbbox((0, 0), line, font=font_bold)
                text_width_artist = bbox_artist[2] - bbox_artist[0]
                text_height_artist = bbox_artist[3] - bbox_artist[1]
                x_artist = (txt_img.width - text_width_artist) // 2
                
                # Dibujar sombra para artista (outline más grueso para efecto bold)
                for adj in [(-3, -3), (-3, 0), (-3, 3), (0, -3), (0, 3), (3, -3), (3, 0), (3, 3),
                           (-2, -2), (-2, 2), (2, -2), (2, 2), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    draw.text((x_artist + adj[0], y_offset + adj[1]), line, font=font_bold, fill=(0, 0, 0, 200))
                # Dibujar artista principal en bold
                draw.text((x_artist - 1, y_offset - 1), line, font=font_bold, fill=(255, 255, 255, 230))
                draw.text((x_artist + 1, y_offset + 1), line, font=font_bold, fill=(255, 255, 255, 230))
                draw.text((x_artist, y_offset), line, font=font_bold, fill=(255, 255, 255, 255))
                y_offset += text_height_artist + 5
            y_offset += 10  # Espaciado después del artista
        
        # Dibujar título en NORMAL (puede ser múltiples líneas, posiblemente con fuente más pequeña)
        if title_lines:
            for line in title_lines:
                bbox_title = draw.textbbox((0, 0), line, font=test_font)
                text_width_title = bbox_title[2] - bbox_title[0]
                text_height_title = bbox_title[3] - bbox_title[1]
                x_title = (txt_img.width - text_width_title) // 2
                
                # Dibujar sombra para título (outline)
                for adj in [(-2, -2), (-2, 2), (2, -2), (2, 2), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    draw.text((x_title + adj[0], y_offset + adj[1]), line, font=test_font, fill=(0, 0, 0, 200))
                # Dibujar título principal en normal
                draw.text((x_title, y_offset), line, font=test_font, fill=(255, 255, 255, 255))
                y_offset += text_height_title + 5
        
        # Si no hay artista ni título, usar texto por defecto
        if (not artist or not artist.strip()) and (not title or not title.strip()):
            default_text = "Unknown"
            bbox = draw.textbbox((0, 0), default_text, font=font_normal)
                        text_width = bbox[2] - bbox[0]
                        x = (txt_img.width - text_width) // 2
                        for adj in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
                draw.text((x + adj[0], y_offset + adj[1]), default_text, font=font_normal, fill=(0, 0, 0, 200))
            draw.text((x, y_offset), default_text, font=font_normal, fill=(255, 255, 255, 255))
                    
                    # Guardar temporalmente
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                    txt_img.save(temp_file.name, 'PNG')
                    temp_file.close()
                    temp_files.append(temp_file.name)
                    
        # Crear clip directamente con el tamaño correcto (no usar resize de MoviePy)
                    txt_clip = ImageClip(temp_file.name, duration=duration)
            txt_clip = txt_clip.set_duration(duration)
            txt_clip = txt_clip.set_position(('center', VideoGenerator.VIDEO_HEIGHT - 200))
            
            # Almacenar archivos temporales como atributo para limpieza posterior
            txt_clip._temp_files = temp_files
            
            return txt_clip
    
    def generate_video(
        self,
        audio_path: str,
        cover_path: str,
        output_path: str,
        artist: str,
        title: str,
        start_time: float,
        end_time: float
    ) -> str:
        """
        Genera el video final combinando todos los elementos.
        
        Args:
            audio_path: Ruta del archivo de audio
            cover_path: Ruta de la imagen de portada
            output_path: Ruta donde guardar el video
            artist: Nombre del artista
            title: Título de la canción
            start_time: Segundo de inicio
            end_time: Segundo de fin
        
        Returns:
            Ruta del video generado
        """
        try:
            # Calcular duración
            duration = end_time - start_time
            
            # Cargar y recortar audio
            audio_clip = AudioFileClip(audio_path)
            audio_clip = audio_clip.subclip(start_time, end_time)
            
            # Crear fondo animado basado en colores de la portada
            background = self.create_animated_background(duration, cover_path=cover_path)
            if background is None:
                raise ValueError("Error: No se pudo crear el fondo animado")
            
            # Crear vinilo girando
            vinyl = self.create_rotating_vinyl(cover_path, duration)
            if vinyl is None:
                raise ValueError("Error: No se pudo crear el vinilo rotatorio")
            
            # Crear texto
            text_overlay = self.create_text_overlay(artist, title, duration)
            if text_overlay is None:
                raise ValueError("Error: No se pudo crear el overlay de texto")
            
            # Filtrar clips None antes de compositar
            clips = [background, vinyl, text_overlay]
            clips = [c for c in clips if c is not None]
            
            if len(clips) == 0:
                raise ValueError("Error: No hay clips válidos para compositar")
            
            # Compositar todo
            final_video = CompositeVideoClip(
                clips,
                size=(self.VIDEO_WIDTH, self.VIDEO_HEIGHT)
            )
            
            # Agregar audio
            final_video = final_video.set_audio(audio_clip)
            final_video = final_video.set_duration(duration)
            final_video = final_video.set_fps(self.FPS)
            
            # Asegurar que el directorio de salida existe
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Exportar con mejor calidad y anti-aliasing
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                fps=self.FPS,
                bitrate='12000k',  # Mayor bitrate para mejor calidad
                preset='slow',     # Preset más lento = mejor calidad
                threads=4,
                logger=None,  # Reducir output
                ffmpeg_params=[
                    '-crf', '18',           # Calidad constante alta (18 es muy buena calidad)
                    '-pix_fmt', 'yuv420p',  # Formato de píxeles compatible
                    '-movflags', '+faststart',  # Optimización para streaming
                    '-vf', 'scale=1080:1350:flags=lanczos'  # Escalado con Lanczos para mejor anti-aliasing
                ]
            )
            
            # Limpiar clips
            audio_clip.close()
            background.close()
            vinyl.close()
            text_overlay.close()
            final_video.close()
            
            # Limpiar archivos temporales de texto
            try:
                if hasattr(text_overlay, '_temp_files'):
                    for temp_file in text_overlay._temp_files:
                        if os.path.exists(temp_file):
                            try:
                                os.remove(temp_file)
                            except:
                                pass
            except:
                pass
            
            # Limpiar archivos temporales de máscara
            try:
                if hasattr(vinyl, '_temp_mask_path') and vinyl._temp_mask_path:
                    temp_mask_path = vinyl._temp_mask_path
                    if os.path.exists(temp_mask_path):
                        try:
                            os.remove(temp_mask_path)
                        except Exception as e:
                            print(f"Error eliminando archivo temporal de máscara: {e}")
            except Exception as e:
                print(f"Error limpiando archivos temporales de máscara: {e}")
            
            return output_path
            
        except Exception as e:
            print(f"Error generando video: {e}")
            raise

