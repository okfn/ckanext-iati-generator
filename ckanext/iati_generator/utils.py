import os
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


def create_or_update_iati_resource(context, package_id, xml_path, existing_resource_id=None):
    """
    Crea o actualiza un recurso XML en un dataset CKAN.

    - Si existing_resource_id es None, se crea un nuevo recurso.
    - Si existe, se actualiza el recurso con el nuevo archivo XML.
    """

    xml_filename = os.path.basename(xml_path)
    with open(xml_path, "rb") as fp:
        resource_data = {
            "package_id": package_id,
            "upload": (fp, xml_filename),
            "format": "XML",
            "name": xml_filename,
            "url_type": "upload",
            "url": xml_filename,
            "description": "Automatically generated file from CSV"
        }

        if existing_resource_id:
            resource_data["id"] = existing_resource_id
            return toolkit.get_action("resource_update")(context, resource_data)
        else:
            return toolkit.get_action("resource_create")(context, resource_data)
