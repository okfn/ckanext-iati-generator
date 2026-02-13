import io
import logging

from ckan.plugins import toolkit

from werkzeug.datastructures import FileStorage

from ckanext.iati_generator import helpers as h
from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE

log = logging.getLogger(__name__)


def process_validation_failures(dataset, validation_issues):
    """
    Identifica qué recursos fallaron y actualiza su estado en la base de datos (IATIFile).
    Retorna los issues normalizados listos para ser usados en ValidationError.
    """
    # Mapping: Nombre de archivo -> Código IATIFileTypes (string)
    mapping = {
        "activities.csv": "200", "participating_orgs.csv": "210",
        "sectors.csv": "220", "budgets.csv": "230", "transactions.csv": "240",
        "transaction_sectors.csv": "250", "locations.csv": "260",
        "documents.csv": "270", "results.csv": "280", "indicators.csv": "290",
        "indicator_periods.csv": "300", "activity_date.csv": "310",
        "contact_info.csv": "320", "conditions.csv": "330",
        "descriptions.csv": "340", "country_budget_items.csv": "350"
    }

    # 1. Identificar archivos únicos que fallaron
    failed_files_map = {}
    for issue in validation_issues:
        fname = issue.file_name
        if fname and fname not in failed_files_map:
            failed_files_map[fname] = issue.message

    # 2. Obtener IATIFiles del namespace actual
    namespace = h.normalize_namespace(dataset.get("iati_namespace", DEFAULT_NAMESPACE))
    files_by_res = h.iati_files_by_resource(namespace=namespace)

    # 3. Actualizar la DB una sola vez por recurso
    for resource in dataset.get("resources", []):
        file_type = str(resource.get("iati_file_type", ""))

        # Verificar si este recurso coincide con algún archivo fallido
        for fname, error_msg in failed_files_map.items():
            target_type = mapping.get(fname)
            if target_type and target_type == file_type:
                res_id = resource['id']
                if res_id in files_by_res:
                    files_by_res[res_id].track_processing(
                        success=False,
                        error_message=error_msg
                    )

    # Retornamos los errores normalizados para la UI
    return h.normalize_iati_errors(validation_issues)


def upload_or_update_xml_resource(context, dataset, file_path, file_name, file_type_enum):
    """
    Sube el archivo XML generado a CKAN.
    Si ya existe un recurso de ese tipo (FINAL_ACTIVITY_FILE), lo actualiza (patch).
    Si no, crea uno nuevo.
    """
    # Buscar recurso existente
    existing_resource = None
    for res in dataset.get("resources", []):
        if int(res.get("iati_file_type", 0)) == file_type_enum.value:
            existing_resource = res
            break

    # Preparar archivo para subida
    with open(file_path, "rb") as f:
        stream = io.BytesIO(f.read())
    upload = FileStorage(stream=stream, filename=file_name)

    res_dict = {
        "name": file_name,
        "url_type": "upload",
        "upload": upload,
        "iati_file_type": file_type_enum.value,
        "format": "XML",
    }

    if existing_resource:
        res_dict["id"] = existing_resource["id"]
        result = toolkit.get_action("resource_patch")({}, res_dict)
        log.info(f"Patched {file_name} resource {result['id']}.")
    else:
        res_dict["package_id"] = dataset["id"]
        result = toolkit.get_action("resource_create")({}, res_dict)
        log.info(f"Created new {file_name} resource with id {result['id']}.")

    return result
