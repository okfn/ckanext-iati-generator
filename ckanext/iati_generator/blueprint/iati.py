from flask import Blueprint, send_from_directory
import os
from ckan.plugins import toolkit
from ckanext.iati_generator.decorators import require_sysadmin_user


iati_blueprint = Blueprint("iati_generator", __name__, url_prefix="/iati-dataset")


@iati_blueprint.route("/static-iati/<resource_id>/<filename>")
@require_sysadmin_user
def serve_iati_file(resource_id, filename):
    """
    Serves a dynamically generated IATI XML file from CKAN's local storage.

    The expected file path is:
        /storage/resources/<first_3>/<next_3>/<resource_id>/<filename>

    This function allows generated XML files to be accessible via a public URL,
    without relying on `url_type="upload"` or a web server like NGINX.

    Requires the user to be authenticated as a sysadmin.
    """
    storage_root = toolkit.config.get("ckan.storage_path")
    dir_path = os.path.join(
        storage_root, "resources",
        resource_id[:3],
        resource_id[3:6],
        resource_id
    )
    file_path = os.path.join(dir_path, filename)

    if not os.path.isfile(file_path):
        return toolkit.abort(404, toolkit._("XML file not found"))
    # TODO check if CKAN FlaskApp -> MultiStaticFlask.send_static_file is a better option
    return send_from_directory(directory=dir_path, path=filename)
