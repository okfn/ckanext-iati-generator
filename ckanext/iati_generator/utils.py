import os
from datetime import datetime
import ckan.lib.uploader as uploader
from ckan.plugins import toolkit
from okfn_iati import (
    IatiActivities, IatiXmlGenerator
)


def get_resource_file_path(context, resource_id):
    """ Validate the resource and get the file path.
        Returns the file path if valid, otherwise raises a ValidationError.
    """

    if not resource_id:
        raise toolkit.ValidationError(
            {"resource_id": "Resource ID is required."}
        )

    resource = toolkit.get_action("resource_show")(context, {"id": resource_id})
    fmt = resource.get("format", "").lower()
    if fmt != "csv":
        raise toolkit.ValidationError(
            {"format": "Unsupported format. Only CSV is allowed."}
        )
    if resource.get("url_type") != "upload":
        raise toolkit.ValidationError(
            {"url_type": "Resource must be a local upload."}
        )

    up = uploader.get_resource_uploader(resource)
    return up.get_path(resource_id)


def generate_final_iati_xml(activities):
    """ Generate the final IATI XML from the activities list.
        Returns the XML string.
    """
    # Generate the IATI XML
    container = IatiActivities(version="2.03", activities=activities)
    generator = IatiXmlGenerator()
    xml_string = generator.generate_iati_activities_xml(container)
    return xml_string


def create_or_update_iati_resource(context, package_id, xml_string, resource_name, existing_resource_id=None):
    """
    Creates or updates an XML resource in a CKAN dataset.
    The physical file is saved under /storage/resources/<3>/<3>/<resource_id>/filename
    """

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    clean_name = resource_name.replace(" ", "_").lower()
    filename = f"{clean_name}_iati_{timestamp}.xml"

    resource_data = {
        "package_id": package_id,
        "format": "XML",
        "name": filename,
        "url_type": "upload",
        "url": filename,
        "description": "Automatically generated file from CSV"
    }

    if existing_resource_id:
        resource_data["id"] = existing_resource_id
        created = toolkit.get_action("resource_update")(context, resource_data)
    else:
        created = toolkit.get_action("resource_create")(context, resource_data)

    # Ahora que tenemos el resource_id, generamos el archivo en la ruta correcta
    resource_id = created["id"]
    storage_root = toolkit.config.get("ckan.storage_path", "/app/storage")
    resource_dir = os.path.join(
        storage_root,
        "resources",
        resource_id[:3],
        resource_id[3:6],
        resource_id
    )
    os.makedirs(resource_dir, exist_ok=True)

    out_path = os.path.join(resource_dir, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml_string)

    return created
