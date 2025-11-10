# Fuentes Personalizadas

Esta carpeta es para almacenar archivos de fuente personalizados que se usarán en la generación de videos.

## Cómo usar fuentes personalizadas

### Opción 1: Colocar archivos de fuente en esta carpeta (Recomendado)

1. Coloca tus archivos de fuente en esta carpeta (`fonts/`)
2. Nombra los archivos siguiendo estos formatos:
   - `Helvetica.ttf` (fuente regular)
   - `Helvetica-Bold.ttf` (fuente en negrita)
   - `Helvetica-Light.ttf` (fuente light)
   - `Helvetica-Regular.ttf` (fuente regular)

### Formatos soportados

- `.ttf` (TrueType Font)
- `.otf` (OpenType Font)
- `.ttc` (TrueType Collection)

### Ejemplos de nombres de archivo

Para usar Helvetica:
- `Helvetica.ttf`
- `Helvetica-Bold.ttf`
- `Helvetica-Light.ttf`

Para usar otra fuente (ej: Arial):
- `Arial.ttf`
- `Arial-Bold.ttf`

### Cambiar la fuente por defecto

Si quieres cambiar la fuente por defecto, edita el archivo `app/services/video_generator.py` y modifica:

```python
DEFAULT_FONT_NAME = "Helvetica"  # Cambia esto a tu fuente
```

## Búsqueda de fuentes

El sistema busca fuentes en este orden:

1. **Carpeta `fonts/` del proyecto** (prioridad más alta)
2. Fuentes del sistema (macOS: `/System/Library/Fonts/`)
3. Fuentes del usuario (`~/Library/Fonts/`)
4. Fuente por defecto del sistema (si no se encuentra ninguna)

## Notas

- Si colocas una fuente en esta carpeta, se usará automáticamente
- No es necesario reiniciar el servidor, las fuentes se cargan cada vez que se genera un video
- Si la fuente no se encuentra, se usará la fuente por defecto del sistema

