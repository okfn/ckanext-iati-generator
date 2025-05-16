import os
import tempfile
from ckan.plugins import toolkit


def iati_generate_test_xml(context, data_dict):
    resource_id = data_dict["resource_id"]
    resource = toolkit.get_action("resource_show")(context, {"id": resource_id})
    csv_url = resource["url"]

    # Aquí podrías usar pandas o csv.reader para cargar el CSV
    logs = []
    try:
        import pandas as pd

        df = pd.read_csv(csv_url)
        logs.append(f"CSV loaded with {len(df)} rows")

        # Ejemplo simple: convertir cada fila en un nodo XML
        from xml.etree.ElementTree import Element, SubElement, ElementTree

        root = Element("iati-data")
        for _, row in df.iterrows():
            activity = SubElement(root, "activity")
            for col in df.columns:
                el = SubElement(activity, col)
                el.text = str(row[col])

        tmp_path = os.path.join(tempfile.gettempdir(), f"iati_test_{resource_id}.xml")
        ElementTree(root).write(tmp_path, encoding="utf-8", xml_declaration=True)

        logs.append(f"XML generated at: {tmp_path}")

        return {"file_path": tmp_path, "logs": "\n".join(logs)}

    except Exception as e:
        raise toolkit.ValidationError({"error": str(e)})
