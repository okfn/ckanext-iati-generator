from flask import Blueprint, render_template, request, redirect, url_for, flash
from ckan.plugins import toolkit
from ckanext.iati_generator.decorators import require_sysadmin_user
from ckanext.iati_generator.utils import create_or_update_iati_resource

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
    logs = result.get("logs", [])
    xml_string = result.get("xml_string")
    resource_name = result.get("resource_name")

    xml_url = None
    if not xml_string:
        # If the XML generation failed, log the error
        flash(toolkit._("Could not generate the XML file. Check the logs below."), "error")
    else:
        # Check if there is already an existing XML resource saved as an extra
        pkg = toolkit.get_action("package_show")(context, {"id": package_id})
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
        flash(toolkit._("XML file uploaded successfully."), "success")

    # Render the same page with the logs and the link to the XML
    pkg = toolkit.get_action("package_show")(context, {"id": package_id})
    return render_template(
        "package/iati_page.html",
        pkg=pkg,
        pkg_dict=pkg,
        logs=logs,
        xml_url=xml_url
    )
