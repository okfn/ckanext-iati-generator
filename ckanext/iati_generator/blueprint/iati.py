import io
from flask import Blueprint, render_template, request, redirect, url_for, flash
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
    result = toolkit.get_action("iati_generate_test_xml")(context, {"resource_id": resource_id})
    logs = result.get("logs", "")
    xml_string = result.get("xml_string")

    xml_url = None
    if not xml_string:
        flash("Could not generate the XML file. Check the logs below.", "error")
    else:
        # --- here we replace the tmpdir with CKAN's uploader API ---
        filename = f"iati_{resource_id}.xml"
        file_obj = io.BytesIO(xml_string.encode("utf-8"))
        # toolkit.upload_to_file_storage uses the configured backend (local or S3)
        upload_dict = toolkit.upload_to_file_storage(file_obj, filename=filename)

        # prepare the data for resource_update
        data_dict = {
            "id":       resource_id,
            "upload":   upload_dict,
            "format":   "XML",
            "name":     filename,
        }
        updated = toolkit.get_action("resource_update")(context, data_dict)
        # CKAN has already saved the file and returned the URL
        xml_url = updated.get("url")
        flash("XML file uploaded successfully.", "success")

    # Render the same page with the logs and the link to the XML
    pkg = toolkit.get_action("package_show")(context, {"id": package_id})
    return render_template(
        "package/iati_page.html",
        pkg=pkg,
        pkg_dict=pkg,
        logs=logs,
        xml_url=xml_url
    )
