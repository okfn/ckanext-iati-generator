import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from ckan.lib.uploader import ResourceUpload
from ckan.plugins import toolkit
from ckanext.iati_generator.decorators import require_sysadmin_user

iati_blueprint = Blueprint("iati_generator", __name__, url_prefix="/iati-dataset")


@iati_blueprint.route("/<package_id>", methods=["GET"])
@require_sysadmin_user
def iati_page(package_id):
    context = {"user": toolkit.c.user}
    # Fetch the package using package_show
    try:
        pkg_dict = toolkit.get_action("package_show")(context, {"id": package_id})
    except toolkit.ObjectNotFound:
        return toolkit.abort(404, toolkit._("Dataset not found"))

    # Pass both pkg and pkg_dict to the template (CKAN templates use both)
    return render_template(
        "package/iati_page.html",
        pkg=pkg_dict,
        pkg_dict=pkg_dict
    )


@iati_blueprint.route("/<package_id>/generate", methods=["POST"])
@require_sysadmin_user
def generate_test_iati(package_id):
    context = {"user": toolkit.c.user}
    resource_id = request.form.get("resource_id")

    if not resource_id:
        flash(toolkit._("Resource ID is required"), "error")
        return redirect(url_for("iati_generator.iati_page", package_id=package_id))

    # Call the action that generates the XML and returns xml_string + logs
    result = toolkit.get_action("generate_iati_xml")(context, {"resource_id": resource_id})
    logs = result.get("logs", "")
    file_path = result.get("file_path")

    xml_url = None
    if not file_path:
        flash(toolkit._("Could not generate the XML file. Check the logs below."), "error")
    else:
        # Get the filename from the file path
        xml_filename = os.path.basename(file_path)

        with open(file_path, "rb") as fp:
            # 2. Create resource_data with tuple (file, filename)
            resource_data = {
                "package_id": package_id,
                "upload": (fp, xml_filename),
                "format": "XML",
                "name": xml_filename,
                "url_type": "upload",
                "description": "Automatically generated file from CSV"
            }
            # 3. Physically upload the file to storage
            uploader = ResourceUpload(resource_data)
            uploader.upload(package_id)

            # 4. Create the resource in CKAN (with the file already saved)
            created = toolkit.get_action("resource_create")(context, resource_data)

            # 5. Build the download URL to display in the view
            xml_url = f"/dataset/{package_id}/resource/{created['id']}/download/{created['name']}"

            flash(toolkit._("XML file uploaded successfully as a new resource."), "success")

    # Render the same page with the logs and the link to the XML
    pkg = toolkit.get_action("package_show")(context, {"id": package_id})
    return render_template(
        "package/iati_page.html",
        pkg=pkg,
        pkg_dict=pkg,
        logs=logs,
        xml_url=xml_url
    )
