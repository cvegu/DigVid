import os
from PIL import Image, ImageFilter
import numpy as np


class ImageProcessor:
    """Procesador para manipular imágenes de portada."""
    
    # Tamaño estándar de Instagram vertical
    VIDEO_WIDTH = 1080
    VIDEO_HEIGHT = 1350
    
    # Tamaño del vinilo (circular) en el video
    VINYL_SIZE = 800
    
    @staticmethod
    def prepare_cover_image(cover_path: str, output_path: str, size: int = VINYL_SIZE) -> str:
        """
        Prepara la imagen de portada para el video.
        Redimensiona, recorta y aplica efectos para que se vea bien girando.
        
        Args:
            cover_path: Ruta de la imagen original
            output_path: Ruta donde guardar la imagen procesada
            size: Tamaño del vinilo (cuadrado)
        
        Returns:
            Ruta de la imagen procesada
        """
        try:
            # Asegurar que el directorio de salida existe
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Cargar imagen
            img = Image.open(cover_path)
            
            # Convertir a RGB si es necesario
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Redimensionar manteniendo aspecto, luego recortar al centro
            width, height = img.size
            
            # Calcular escala para que la imagen cubra el área
            scale = max(size / width, size / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # Redimensionar
            img = img.resize((new_width, new_height), Image.Resampling.BICUBIC)
            
            # Recortar al centro
            left = (new_width - size) // 2
            top = (new_height - size) // 2
            right = left + size
            bottom = top + size
            
            img = img.crop((left, top, right, bottom))
            
            # Aplicar un ligero sharpen para que se vea mejor
            img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
            
            # Guardar
            img.save(output_path, 'JPEG', quality=95)
            return output_path
            
        except Exception as e:
            print(f"Error procesando imagen: {e}")
            import traceback
            traceback.print_exc()
            # Crear una imagen placeholder si hay error
            try:
                output_dir = os.path.dirname(output_path)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                placeholder = Image.new('RGB', (size, size), color=(50, 50, 50))
                placeholder.save(output_path, 'JPEG')
                return output_path
            except Exception as e2:
                print(f"Error creando placeholder de fallback: {e2}")
                raise
    
    @staticmethod
    def create_placeholder_cover(output_path: str, size: int = VINYL_SIZE) -> str:
        """
        Crea una imagen placeholder para cuando no hay portada.
        
        Args:
            output_path: Ruta donde guardar la imagen
            size: Tamaño de la imagen
        
        Returns:
            Ruta de la imagen creada
        """
        try:
            # Asegurar que el directorio existe
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Crear imagen con gradiente simple
            img = Image.new('RGB', (size, size), color=(40, 40, 60))
            
            # Agregar un círculo en el centro (como un vinilo)
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            
            # Círculo exterior
            margin = 20
            draw.ellipse(
                [margin, margin, size - margin, size - margin],
                fill=(60, 60, 80),
                outline=(100, 100, 120),
                width=5
            )
            
            # Círculo interior (centro del vinilo)
            center_size = 100
            center_x = size // 2
            center_y = size // 2
            draw.ellipse(
                [
                    center_x - center_size // 2,
                    center_y - center_size // 2,
                    center_x + center_size // 2,
                    center_y + center_size // 2
                ],
                fill=(40, 40, 60),
                outline=(80, 80, 100),
                width=3
            )
            
            img.save(output_path, 'JPEG', quality=95)
            return output_path
        except Exception as e:
            print(f"Error creando portada placeholder: {e}")
            import traceback
            traceback.print_exc()
            raise

