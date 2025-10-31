from flask import Blueprint, abort

from ckan.plugins import toolkit
from ckan import model
from ckanext.iati_generator.models.iati_files import IATIFile
from ckanext.iati_generator.models.enums import IATIFileTypes

public_iati_blueprint = Blueprint("iati_public", __name__, url_prefix="/iati")


@public_iati_blueprint.route("/<namespace>/<filename>")
def serve_public_iati(namespace, filename):
    """
    Public endpoint that serves or redirects IATI XML files.
    Example:
        /iati/bcie/organization.xml
        /iati/bcie/activities.xml
    """
    # Map filename -> enum type
    if filename.lower() == "organization.xml":
        file_type = IATIFileTypes.ORGANIZATION_MAIN_FILE.value
    elif filename.lower() == "activities.xml":
        file_type = IATIFileTypes.ACTIVITY_MAIN_FILE.value
    else:
        abort(404, "Unknown IATI file type")

    # Query the DB for the matching file
    session = model.Session
    file = (
        session.query(IATIFile)
        .filter_by(namespace=namespace, file_type=file_type)
        .first()
    )
    if not file:
        abort(404, f"No IATI file found for namespace '{namespace}' and type '{filename}'")

    # Redirect to the resource URL (the resource points to the static file)
    resource = toolkit.get_action("resource_show")({}, {"id": file.resource_id})
    url = resource.get("url")
    if not url:
        abort(404, "Resource URL not found")
    return toolkit.redirect(url)
