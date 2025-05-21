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
