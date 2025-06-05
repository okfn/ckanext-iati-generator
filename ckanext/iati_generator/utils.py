import os
import re
import tempfile
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
    Creates or updates an XML resource within a CKAN dataset from a generated XML string.

    The XML file is physically saved at:
        /storage/resources/<first_3>/<next_3>/<resource_id>/<filename>

    Then, a resource is registered in CKAN with a static URL served via a custom Flask endpoint.

    Args:
        context (dict): CKAN context with the current user.
        package_id (str): CKAN dataset ID.
        xml_string (str): Generated IATI XML content.
        resource_name (str): Base name for the file.
        existing_resource_id (str|None): If provided, updates that resource instead of creating a new one.

    Returns:
        dict: The created or updated CKAN resource.
    """
    # Generar identificador legible basado en el nombre + timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    clean_base = re.sub(r'[^a-zA-Z0-9_-]', '_', resource_name).lower()
    slug_name = f"{clean_base}_iati_{timestamp}"

    # Crear archivo temporal
    with tempfile.NamedTemporaryFile("w+b", delete=False, suffix=".xml") as tmp:
        tmp.write(xml_string.encode("utf-8"))
        tmp.flush()
        tmp_path = tmp.name

    # Datos del recurso
    resource_data = {
        "package_id": package_id,
        "name": slug_name,
        "format": "XML",
        "url_type": "upload",
        "description": f"IATI XML generated from CSV at {timestamp}"
    }

    # Subir archivo a CKAN
    with open(tmp_path, "rb") as f:
        resource_data["upload"] = f
        if existing_resource_id:
            resource_data["id"] = existing_resource_id
            created = toolkit.get_action("resource_update")(context, resource_data)
        else:
            created = toolkit.get_action("resource_create")(context, resource_data)

    os.unlink(tmp_path)

    return created
