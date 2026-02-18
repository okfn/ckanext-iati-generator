import io
import logging

from ckan.plugins import toolkit

from werkzeug.datastructures import FileStorage

from ckanext.iati_generator import helpers as h
from ckanext.iati_generator.models.enums import CSV_FILENAME_TO_FILE_TYPE
from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE

log = logging.getLogger(__name__)


def process_validation_failures(dataset, validation_issues):
    """
    Identifies which resources failed and updates their status in the database (IATIFile).
    Returns the normalized issues ready to be used in ValidationError.
    """
    failed_files_map = {}
    for issue in validation_issues:
        fname = issue.file_name
        if fname and fname not in failed_files_map:
            failed_files_map[fname] = issue.message

    namespace = h.normalize_namespace(dataset.get("iati_namespace", DEFAULT_NAMESPACE))
    files_by_res = h.iati_files_by_resource(namespace=namespace)

    for resource in dataset.get("resources", []):
        file_type = str(resource.get("iati_file_type", ""))

        for fname, error_msg in failed_files_map.items():
            target_type = CSV_FILENAME_TO_FILE_TYPE.get(fname)
            if target_type and target_type == file_type:
                res_id = resource['id']
                if res_id in files_by_res:
                    files_by_res[res_id].track_processing(
                        success=False,
                        error_message=error_msg
                    )
    return h.normalize_iati_errors(validation_issues)


def upload_or_update_xml_resource(context, dataset, file_path, file_name, file_type_enum):
    """
    Uploads the generated XML file to CKAN.
    If a resource of that type (FINAL_ACTIVITY_FILE) already exists, it updates (patches) it.
    If not, it creates a new one.
    """
    existing_resource = None
    for res in dataset.get("resources", []):
        if int(res.get("iati_file_type", 0)) == file_type_enum.value:
            existing_resource = res
            break

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
