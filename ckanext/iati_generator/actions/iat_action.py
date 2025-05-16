import os
import tempfile
import csv
import ckan.lib.uploader as uploader
from ckan.plugins import toolkit
from xml.etree.ElementTree import Element, SubElement, ElementTree


def iati_generate_test_xml(context, data_dict):
    resource_id = data_dict["resource_id"]
    resource = toolkit.get_action("resource_show")(context, {"id": resource_id})

    logs = []

    try:
        # Obtener la ruta local del archivo
        logs.append(f"resource_id: {resource_id} ({type(resource_id)})")

        resource = toolkit.get_action("resource_show")(context, {"id": resource_id})
        logs.append(f"resource keys: {list(resource.keys())}")

        if not isinstance(resource, dict):
            raise Exception("resource is not a dict")

        upload = uploader.get_resource_uploader(resource)
        local_path = upload.get_path(resource)

        logs.append(f"Reading CSV from local path: {local_path}")

        # Leer el archivo directamente desde disco
        with open(local_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            logs.append(f"CSV contains {len(rows)} rows")

        # Crear XML
        root = Element("iati-data")
        for i, row in enumerate(rows):
            activity = SubElement(root, "activity")
            for key, value in row.items():
                el = SubElement(activity, key)
                el.text = value or ""
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
        raise toolkit.ValidationError({"error": str(e)})
