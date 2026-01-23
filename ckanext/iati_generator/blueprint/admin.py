from ckan.plugins import toolkit
from flask import Blueprint

from ckanext.iati_generator import helpers as h
from ckanext.iati_generator.models.enums import IATIFileTypes

iati_file_admin = Blueprint("iati_generator_admin_files", __name__)


def _get_iati_display_name(code):
    name = ""
    try:
        name = IATIFileTypes(int(code)).name
    except ValueError:
        name = "Wrong code name"
    return name.replace("_", " ").title()


@iati_file_admin.route("/dataset/iati-files/<package_id>")
def iati_files_index(package_id):
    """List IATI files and missing files for the selected dataset."""
    toolkit.check_access("iati_generate_xml_files", {"user": toolkit.c.user}, {"package_id": package_id})

    dataset = toolkit.get_action('package_show')({}, {"id": package_id})

    rows_out = []
    for resource in dataset["resources"]:
        iati_file_type = resource.get("iati_file_type", "")
        if iati_file_type:
            url = toolkit.url_for(
                "resource.read",
                package_type=dataset["type"],
                id=dataset["id"],
                resource_id=resource["id"]
            )
            rows_out.append({
                "file_type": _get_iati_display_name(iati_file_type),
                "resource_name": resource.get("name") or resource.get("id"),
                "resource_url": url,
            })

    pending_files = h.get_pending_mandatory_files(dataset["id"])

    return toolkit.render(
        "package/iati_files.html",
        {
            "pkg_dict": dataset,  # Required for package/read_base.html
            "package_id": package_id,
            "iati_files": rows_out,
            "pending_files": pending_files,
        },
    )


def iati_files_errors(package_id, errors):
    """Render the list of IATI errors for the selected dataset while generating IATI XML file."""
    pkg_dict = toolkit.get_action('package_show')({}, {"id": package_id})
    return toolkit.render(
        "package/iati_errors.html", {
            "pkg_dict": pkg_dict,
            "errors": errors,
            "iati_files_url": toolkit.url_for("iati_generator_admin_files.iati_files_index", package_id=package_id),
        },
    )


@iati_file_admin.route("/generate-iati-activity_file/<package_id>", methods=["POST"])
def generate_iati_activity_file(package_id):
    ctx = {"user": toolkit.c.user}
    data_dict = {"package_id": package_id}

    toolkit.check_access("iati_generate_xml_files", ctx, data_dict)
    errors = None
    try:
        resource = toolkit.get_action("iati_generate_activities_xml")(ctx, data_dict)
    except toolkit.ValidationError as e:
        errors = e.error_dict if hasattr(e, 'error_dict') else None
        toolkit.h.flash_error(
            toolkit._("There was an error generating the IATI file probably due to missing on wrong-formatted files.")
        )
        return iati_files_errors(package_id, errors)

    try:
        res_url = toolkit.url_for("resource.read", package_type="dataset", id=resource["package_id"], resource_id=resource["id"])
    except toolkit.ObjectNotFound:
        errors = ['The dataset does not exist']
        toolkit.h.flash_error(toolkit._(f"The dataset with id {package_id} does not exist."))
        return iati_files_errors(package_id, errors)

    msg = toolkit._(f"IATI File generated successfully, you can <a href={res_url}>click here to go to the resource.</a>")
    toolkit.h.flash_success(msg, allow_html=True)

    redirect_url = toolkit.url_for("iati_generator_admin_files.iati_files_index", package_id=package_id)
    return toolkit.redirect_to(redirect_url)


@iati_file_admin.route("/generate-iati-organisation_file/<package_id>", methods=["POST"])
def generate_iati_organisation_file(package_id):
    ctx = {"user": toolkit.c.user}
    data_dict = {"package_id": package_id}

    toolkit.check_access("iati_generate_xml_files", ctx, data_dict)
    errors = None
    try:
        resource = toolkit.get_action("iati_generate_organisation_xml")(ctx, data_dict)
    except toolkit.ValidationError as e:
        errors = e.error_dict if hasattr(e, 'error_dict') else None
        toolkit.h.flash_error(
            toolkit._("There was an error generating the IATI file probably due to missing on wrong-formatted files.")
        )
        return iati_files_errors(package_id, errors)

    try:
        res_url = toolkit.url_for("resource.read", package_type="dataset", id=resource["package_id"], resource_id=resource["id"])
    except toolkit.ObjectNotFound:
        errors = ['The dataset does not exist']
        toolkit.h.flash_error(toolkit._(f"The dataset with id {package_id} does not exist."))
        return iati_files_errors(package_id, errors)

    msg = toolkit._(f"IATI File generated successfully, you can <a href={res_url}>click here to go to the resource.</a>")
    toolkit.h.flash_success(msg, allow_html=True)

    redirect_url = toolkit.url_for("iati_generator_admin_files.iati_files_index", package_id=package_id)
    return toolkit.redirect_to(redirect_url)
