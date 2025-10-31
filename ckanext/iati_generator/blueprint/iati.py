from flask import Blueprint, send_from_directory
import os
from ckan.lib import base
from ckan.lib.helpers import helper_functions as h
from ckan.plugins import toolkit
from ckan import model as ckan_model

from ckanext.iati_generator.models.iati_files import IATIFile
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.decorators import require_sysadmin_user
from ckanext.iati_generator.utils import create_or_update_iati_resource

iati_blueprint = Blueprint("iati_generator", __name__, url_prefix="/iati-dataset")

_FILENAME_BY_TYPE = {
    IATIFileTypes.ORGANIZATION_MAIN_FILE.value: "organization.xml",
    # IATIFileTypes.ACTIVITY_MAIN_FILE.value: "activities.xml",
    # if you later add more types, add them here
}


def _build_public_iati_links_for_package(package_id):
    """
    Returns a list of dicts with:
    - 'label'  (e.g., 'bcie – organization.xml')
    - 'url'    (e.g., '/iati/bcie/organization.xml')
    - 'status' (optional: 'valid' / 'error' for displaying badges)
    """
    Session = ckan_model.Session
    Resource = ckan_model.Resource

    q = (
        Session.query(IATIFile, Resource)
        .join(Resource, Resource.id == IATIFile.resource_id)
        .filter(Resource.package_id == package_id, Resource.state == "active")
    )

    items = []
    for f, res in q.all():
        filename = _FILENAME_BY_TYPE.get(f.file_type)
        if not filename:
            continue
        public_url = f"/iati/{f.namespace}/{filename}"

        label = f"{f.namespace} – {filename}"
        status = "valid" if f.is_valid else "error"

        items.append({
            "label": label,
            "url": public_url,
            "status": status,
            "resource_id": f.resource_id,
        })

    # order alphabetically by label
    items.sort(key=lambda x: x["label"])
    return items


@iati_blueprint.route("/<package_id>", methods=["GET"])
@require_sysadmin_user
def iati_page(package_id):
    # Check configuration flag
    hide_tab = toolkit.asbool(toolkit.config.get("ckanext.iati_generator.hide_tab", False))
    if hide_tab:
        return toolkit.abort(404, toolkit._("Page disabled by configuration"))

    context = {"user": toolkit.c.user}
    # Fetch the package using package_show
    try:
        pkg_dict = toolkit.get_action("package_show")(context, {"id": package_id})
    except toolkit.ObjectNotFound:
        return toolkit.abort(404, toolkit._("Dataset not found"))

    public_links = _build_public_iati_links_for_package(package_id)

    # Pass both pkg and pkg_dict to the template (CKAN templates use both)
    ctx = {
        "pkg": pkg_dict,
        "pkg_dict": pkg_dict,
        "public_iati_links": public_links,
    }
    return base.render("iati/iati_page.html", ctx)


@iati_blueprint.route("/<package_id>/generate", methods=["POST"])
@require_sysadmin_user
def generate_test_iati(package_id):
    context = {"user": toolkit.c.user}
    resource_id = toolkit.request.form.get("resource_id")

    if not resource_id:
        h.flash_error(toolkit._("Resource ID is required"), "error")
        return toolkit.redirect(toolkit.url_for("iati_generator.iati_page", package_id=package_id))

    # Check if there is already an existing XML resource saved as an extra
    pkg = toolkit.get_action("package_show")(context, {"id": package_id})
    if not pkg:
        h.flash_error(toolkit._("Dataset not found"), "error")
        return toolkit.redirect(toolkit.url_for("iati_generator.iati_page", package_id=package_id))
    # Call the action that generates the XML and returns xml_string + logs
    result = toolkit.get_action("generate_iati_xml")(context, {"resource_id": resource_id})
    logs = result.get("logs", [])
    xml_string = result.get("xml_string")
    resource_name = result.get("resource_name")

    xml_url = None
    if not xml_string:
        # If the XML generation failed, log the error
        h.flash_error(toolkit._("Could not generate the XML file. Check the logs below."), "error")
    else:
        extras = {e["key"]: e["value"] for e in pkg.get("extras", [])}
        existing_resource_id = extras.get("iati_base_resource_id")

        # Create or update the resource
        created = create_or_update_iati_resource(
            context=context,
            package_id=package_id,
            xml_string=xml_string,
            resource_name=resource_name,
            existing_resource_id=existing_resource_id
        )

        # If it did not exist before, save it as an extra in the dataset
        if not existing_resource_id:
            toolkit.get_action("package_patch")(context, {
                "id": package_id,
                "extras": [{"key": "iati_base_resource_id", "value": created["id"]}]
            })

        # URL for downloading the XML
        xml_url = f"/dataset/{package_id}/resource/{created['id']}/download/{created['name']}"
        h.flash_success(toolkit._("XML file uploaded successfully."), "success")

    # rebuild the public IATI links
    public_links = _build_public_iati_links_for_package(package_id)

    # Render the same page with the logs and the link to the XML
    ctx = {
        "pkg": pkg,
        "pkg_dict": pkg,
        "logs": logs,
        "xml_url": xml_url,
        "public_iati_links": public_links,
    }
    return base.render("iati/iati_page.html", ctx)


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
