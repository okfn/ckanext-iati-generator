# Quick Start - Script de Integración IATI

Guía rápida para ejecutar el script de carga de datos de prueba.

## En Docker (Recomendado)

```bash
# 1. Entrar al contenedor CKAN
docker exec -it ckan bash

# 2. Activar el entorno virtual y configurar CKAN_INI
source venv/bin/activate
export CKAN_INI=/app/ckan.ini

# 3. Ir al directorio de la extensión
cd src_extensions/ckanext-iati-generator

# 4. Ejecutar el script (opciones)
# Opción A: Ver qué se haría sin ejecutar (dry-run)
python scripts/seed_iati_integration_data.py --organization all --dry-run

# Opción B: Cargar World Bank solamente
python scripts/seed_iati_integration_data.py --organization world-bank --verbose

# Opción C: Cargar Asian Bank solamente
python scripts/seed_iati_integration_data.py --organization asian-bank --verbose

# Opción D: Cargar todo
python scripts/seed_iati_integration_data.py --organization all --verbose
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

### Error: "Please set CKAN_INI"
```bash
export CKAN_INI=/app/ckan.ini
```

### Error: "This script must be run in a CKAN environment"
```bash
source venv/bin/activate
```

### Ver solo los datasets creados sin recursos
```bash
python scripts/seed_iati_integration_data.py --dry-run
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
