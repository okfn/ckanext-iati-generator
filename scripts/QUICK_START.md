# Quick Start - Script de Integración IATI

Guía rápida para ejecutar el script de carga de datos de prueba usando la **API de CKAN**.

## 1. Obtener tu API Key de CKAN

En tu instancia CKAN:

1. Inicia sesión
2. Ve a tu perfil de usuario  
3. Copia tu **API Key**

## 2. Configurar Variables de Entorno (Opcional)

```bash
export CKAN_URL=http://localhost:5000        # o la URL de tu CKAN
export CKAN_API_KEY=TU_API_KEY
```

## 3. Ejecutar el Script

Desde el directorio de la extensión:

```bash
cd src_extensions/ckanext-iati-generator

# Opción A: Ver qué se haría sin ejecutar (dry-run)
python scripts/seed_iati_integration_data.py --organization all --dry-run

# Opción B: Cargar World Bank solamente
python scripts/seed_iati_integration_data.py --organization world-bank --verbose

# Opción C: Cargar Asian Bank solamente
python scripts/seed_iati_integration_data.py --organization asian-bank --verbose

# Opción D: Cargar todo
python scripts/seed_iati_integration_data.py --organization all --verbose
```

**Nota:** Si no usas variables de entorno, puedes pasar `--ckan-url` y `--api-key` directamente:

```bash
python scripts/seed_iati_integration_data.py \
  --ckan-url http://localhost:5000 \
  --api-key TU_API_KEY \
  --organization all
```

## Verificar los Resultados

Después de ejecutar el script, verifica:

1. **Vista de administración de archivos IATI:**
   ```
   http://localhost:5000/ckan-admin/list-iati-files/iati-files
   ```

2. **Datasets creados:**
   - World Bank: `http://localhost:5000/dataset/world-bank-iati-2024`
   - Asian Bank: `http://localhost:5000/dataset/asian-dev-bank-iati`

3. **Verificar namespaces:**
   - World Bank debe tener namespace: `iati-xml`
   - Asian Bank debe tener namespace: `asian-bank`

## Resumen del Output Esperado

```
============================================================
Loading data for: World Bank IATI Data 2024
============================================================

INFO - Creating/updating dataset: world-bank-iati-2024
INFO - Downloading: https://raw.githubusercontent.com/...
INFO - Creating resource: organization.csv
INFO - Creating IATIFile record for resource abc123...
INFO - Downloading: https://raw.githubusercontent.com/...
INFO - Creating resource: names.csv
...

============================================================
Loading data for: Asian Development Bank IATI Data
============================================================

INFO - Creating/updating dataset: asian-dev-bank-iati
...

============================================================
SUMMARY
============================================================
Datasets created/updated: 2
Resources created: 16
IATIFile records created: 16
Errors: 0
============================================================
```

## Troubleshooting Rápido

### Error: "CKAN API key is required"
```bash
# Opción 1: Configurar variable de entorno
export CKAN_API_KEY=TU_API_KEY

# Opción 2: Pasar directamente en el comando
python scripts/seed_iati_integration_data.py --api-key TU_API_KEY --organization all
```

### Error de conexión a CKAN
Verifica que CKAN esté corriendo y la URL sea correcta:
```bash
curl http://localhost:5000/api/3/action/status_show
```

### Ver solo qué se haría sin ejecutar
```bash
python scripts/seed_iati_integration_data.py --organization all --dry-run
```

### Problemas con downloads
Verifica tu conexión a internet y que las URLs en `sample_data_config.yaml` sean correctas.

## Limpiar y Volver a Ejecutar

Si necesitas limpiar y volver a cargar:

```bash
# Eliminar datasets manualmente desde la UI de CKAN o usar la API
# Luego volver a ejecutar el script
python scripts/seed_iati_integration_data.py --organization all --verbose
```

El script detectará si los datasets ya existen y los actualizará en lugar de crear duplicados.

## Ejecutar desde Fuera del Contenedor Docker

El script funciona como herramienta externa - puedes ejecutarlo desde tu máquina local:

```bash
# Desde tu máquina (fuera de Docker)
python scripts/seed_iati_integration_data.py \
  --ckan-url http://localhost:5000 \
  --api-key TU_API_KEY \
  --organization all
```
