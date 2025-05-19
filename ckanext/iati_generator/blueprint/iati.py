import tempfile
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
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
        flash("Resource ID is required", "error")
        return redirect(url_for("iati_generator.iati_page", package_id=package_id))

    result = toolkit.get_action("iati_generate_test_xml")(context, {"resource_id": resource_id})
    logs = result.get("logs", "")

    # Verificamos si se generó correctamente el archivo
    xml_path = result.get("file_path")
    if not xml_path:
        flash("No se pudo generar el archivo XML. Revisá los logs abajo.", "error")

    # Fetch the package using package_show once
    pkg_dict = toolkit.get_action("package_show")(context, {"id": package_id})
    return render_template(
        "package/iati_page.html",
        pkg=pkg_dict,
        pkg_dict=pkg_dict,
        logs=logs,
        xml_download_url=url_for("iati_generator.download_temp_xml", file=os.path.basename(xml_path)) if xml_path else None
    )


@iati_blueprint.route("/download/<file>", methods=["GET"])
@require_sysadmin_user
def download_temp_xml(file):
    path = os.path.join(tempfile.gettempdir(), file)
    return send_file(path, as_attachment=True, mimetype="application/xml")
