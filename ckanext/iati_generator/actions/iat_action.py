import logging
import os
import tempfile
import csv
import traceback
import ckan.lib.uploader as uploader
from ckan.plugins import toolkit
from xml.etree.ElementTree import Element, SubElement, ElementTree

log = logging.getLogger(__name__)

def iati_generate_test_xml(context, data_dict):
    logs = []

    try:
        logs.append(f"DATA_DICT TYPE: {type(data_dict)}")
        logs.append(f"DATA_DICT KEYS: {list(data_dict.keys())}")
        logs.append(f"DATA_DICT FULL: {data_dict}")

        resource_id = data_dict["resource_id"]
        logs.append(f"resource_id: {resource_id} ({type(resource_id)})")

        # Obtener el recurso
        resource = toolkit.get_action("resource_show")(context, {"id": resource_id})
        logs.append(f"resource keys: {list(resource.keys())}")

        # Validar que sea un dict
        if not isinstance(resource, dict):
            raise Exception("resource is not a dict")

        # Obtener ruta local del archivo
        upload = uploader.get_resource_uploader(resource)
        resource_id = resource.get("id")
        logs.append(f"resource['id']: {resource_id} ({type(resource_id)})")

        if not isinstance(resource_id, str):
            raise Exception(f"resource['id'] is not a string: {resource_id} ({type(resource_id)})")

        local_path = upload.get_path(resource)
        logs.append(f"Reading CSV from local path: {local_path}")

        # Leer CSV
        with open(local_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            logs.append(f"CSV contains {len(rows)} rows")

        # Verificar estructura de las filas
        if not all(isinstance(row, dict) for row in rows):
            raise Exception("One or more rows are not dictionaries")

        # Crear XML
        root = Element("iati-data")
        for i, row in enumerate(rows):
            activity = SubElement(root, "activity")

            for key, value in row.items():
                if not isinstance(key, str):
                    logs.append(f"Warning: skipping key of type {type(key)}")
                    continue

                el = SubElement(activity, key)
                el.text = str(value) if value is not None else ""

            if i >= 100:
                logs.append("Truncated at 100 rows to avoid large XML files")
                break

        # Guardar XML en archivo temporal
        tmp_path = os.path.join(tempfile.gettempdir(), f"iati_test_{resource_id}.xml")
        ElementTree(root).write(tmp_path, encoding="utf-8", xml_declaration=True)
        logs.append(f"XML saved at {tmp_path}")

        return {
            "file_path": tmp_path,
            "logs": "\n".join(logs)
        }

    except Exception as e:
        # Captura completa del error con traceback
        error_trace = traceback.format_exc()
        logs.append("Exception occurred:")
        logs.append(error_trace)

        return {
            "logs": "\n".join(logs)
        }
