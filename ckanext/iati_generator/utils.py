import os
import re
import uuid
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
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', resource_name).lower()
    filename = f"{clean_name}_iati_{timestamp}.xml"

    # Determine resource ID (use new UUID if not updating)
    resource_id = existing_resource_id or str(uuid.uuid4())

    # Create the physical directory where the file will be stored
    storage_root = toolkit.config.get("ckan.storage_path", "/app/storage")
    resource_dir = os.path.join(
        storage_root, "resources",
        resource_id[:3],
        resource_id[3:6],
        resource_id
    )
    os.makedirs(resource_dir, exist_ok=True)

    # Write the XML file to disk
    out_path = os.path.join(resource_dir, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml_string)

    # Build the static URL to the file, served by a Flask endpoint
    site_url = toolkit.config.get("ckan.site_url", "http://localhost:5000")
    url = f"{site_url}/iati-dataset/static-iati/{resource_id}/{filename}"

    # Prepare the resource data dictionary
    resource_data = {
        "package_id": package_id,
        "format": "XML",
        "name": filename,
        "url_type": "none",
        "url": url,
        "description": "Automatically generated file from CSV"
    }

    # Create or update the resource in CKAN
    if existing_resource_id:
        resource_data["id"] = existing_resource_id
        created = toolkit.get_action("resource_update")(context, resource_data)
    else:
        created = toolkit.get_action("resource_create")(context, resource_data)

    return created
