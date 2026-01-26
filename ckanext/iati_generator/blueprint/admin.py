from ckan.plugins import toolkit
from flask import Blueprint

from ckanext.iati_generator import helpers as h
from ckanext.iati_generator.decorators import require_sysadmin_user
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

    org_rows = []
    act_rows = []
    for resource in dataset["resources"]:
        iati_file_type = resource.get("iati_file_type", "")
        if iati_file_type:
            try:
                code = int(iati_file_type)
            except (ValueError, TypeError):
                code = None

            url = toolkit.url_for(
                "resource.read",
                package_type=dataset["type"],
                id=dataset["id"],
                resource_id=resource["id"]
            )
            row = {
                "file_type": _get_iati_display_name(iati_file_type),
                "resource_name": resource.get("name") or resource.get("id"),
                "resource_url": url,
            }

            if code is not None and 100 <= code < 200:
                org_rows.append(row)
            elif code is not None and 200 <= code < 400:
                act_rows.append(row)

    pending_files = h.get_pending_mandatory_files(dataset["id"])

    return toolkit.render(
        "package/iati_files.html",
        {
            "pkg_dict": dataset,  # Required for package/read_base.html
            "package_id": package_id,
            "org_files": org_rows,
            "act_files": act_rows,
            "pending_files": pending_files,
        },
    )


@iati_file_admin.route("/generate-iati-activity_file/<package_id>", methods=["POST"])
@require_sysadmin_user
def generate_iati_activity_file(package_id):
    ctx = {"user": toolkit.c.user}
    data_dict = {"package_id": package_id}

    toolkit.check_access("iati_generate_xml_files", ctx, data_dict)
    try:
        resource = toolkit.get_action("iati_generate_activities_xml")(ctx, data_dict)
        res_url = toolkit.url_for("resource.read", package_type="dataset", id=resource["package_id"], resource_id=resource["id"])
        msg = toolkit._(f"IATI File generated successfully, you can <a href={res_url}>click here to go to the resource.</a>")
        toolkit.h.flash_success(msg, allow_html=True)
    except toolkit.ObjectNotFound:
        toolkit.h.flash_error(toolkit._(f"The dataset with id {package_id} does not exist."))
    except toolkit.ValidationError:
        toolkit.h.flash_error(
            toolkit._("There was an error generating the IATI file probably due to missing on wrong-formatted files.")
        )

    redirect_url = toolkit.url_for("iati_generator_admin_files.iati_files_index", package_id=package_id)
    return toolkit.redirect_to(redirect_url)


@iati_file_admin.route("/generate-iati-organisation_file/<package_id>", methods=["POST"])
@require_sysadmin_user
def generate_iati_organisation_file(package_id):
    ctx = {"user": toolkit.c.user}
    data_dict = {"package_id": package_id}

    toolkit.check_access("iati_generate_xml_files", ctx, data_dict)
    try:
        resource = toolkit.get_action("iati_generate_organisation_xml")(ctx, data_dict)
        res_url = toolkit.url_for("resource.read", package_type="dataset", id=resource["package_id"], resource_id=resource["id"])
        msg = toolkit._(f"IATI File generated successfully, you can <a href={res_url}>click here to go to the resource.</a>")
        toolkit.h.flash_success(msg, allow_html=True)
    except toolkit.ObjectNotFound:
        toolkit.h.flash_error(toolkit._(f"The dataset with id {package_id} does not exist."))
    except toolkit.ValidationError:
        toolkit.h.flash_error(
            toolkit._("There was an error generating the IATI file probably due to missing on wrong-formatted files.")
        )

    redirect_url = toolkit.url_for("iati_generator_admin_files.iati_files_index", package_id=package_id)
    return toolkit.redirect_to(redirect_url)
