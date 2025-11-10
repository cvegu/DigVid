# ⚠️ Problema Detectado: Sincronización de OneDrive

## El Problema

El proyecto está en OneDrive y algunos archivos aún no están sincronizados localmente. Esto causa timeouts cuando el servidor intenta leerlos.

## Soluciones

### Opción 1: Esperar a que OneDrive sincronice (Recomendado)

1. Abre el Finder y navega a la carpeta del proyecto
2. Verifica que OneDrive esté sincronizado (ícono de nube debe desaparecer)
3. Ejecuta el script de verificación:
   ```bash
   python3 check_files.py
   ```
4. Cuando todos los archivos estén ✅, inicia el servidor:
   ```bash
   ./start.sh
   ```

### Opción 2: Forzar sincronización

Ejecuta el script de sincronización:
```bash
./sync_files.sh
```

Esto forzará a OneDrive a descargar todos los archivos. Espera unos minutos.

### Opción 3: Mover el proyecto fuera de OneDrive (Mejor para desarrollo)

```bash
# Mover a una carpeta local
mv /Users/cristianvega/Library/CloudStorage/OneDrive-Personal/DigVid ~/DigVid

# O crear un nuevo proyecto
cp -r /Users/cristianvega/Library/CloudStorage/OneDrive-Personal/DigVid ~/DigVid
cd ~/DigVid
```

## Verificar que el servidor funcione

Una vez que los archivos estén sincronizados:

```bash
# Verificar archivos
python3 check_files.py

# Iniciar servidor
./start.sh
```

Luego abre: http://localhost:8000

## Nota

OneDrive puede causar problemas de rendimiento en desarrollo. Para proyectos de desarrollo, es mejor usar una carpeta local como `~/Projects/` o `~/Development/`.

