import logging

from ckan.plugins import toolkit
from flask import Blueprint

from ckanext.iati_generator import helpers as h
from ckanext.iati_generator.models.enums import IATIFileTypes

iati_file_admin = Blueprint("iati_generator_admin_files", __name__)
log = logging.getLogger(__name__)


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
                code = 0

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
        raw = e.error_dict if hasattr(e, 'error_dict') else None
        try:
            errors = h.normalize_iati_errors(raw, package_id=package_id)
            log.debug(f"Normalized errors structure: summary={errors.get('summary')}, items_count={len(errors.get('items', []))}")
        except Exception as normalize_err:
            log.error(f"Error normalizing IATI errors: {normalize_err}", exc_info=True)
            # Fallback: create minimal structure
            errors = {
                "summary": "Error al procesar los errores de validación",
                "items": [{"title": "Error de normalización", "details": str(raw), "suggestion": "Contactá a soporte"}],
                "raw": [str(raw)]
            }

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
        raw = e.error_dict if hasattr(e, 'error_dict') else None
        try:
            errors = h.normalize_iati_errors(raw, package_id=package_id)
            log.debug(f"Normalized errors structure: summary={errors.get('summary')}, items_count={len(errors.get('items', []))}")
        except Exception as normalize_err:
            log.error(f"Error normalizing IATI errors: {normalize_err}", exc_info=True)
            # Fallback: create minimal structure
            errors = {
                "summary": "Error al procesar los errores de validación",
                "items": [{"title": "Error de normalización", "details": str(raw), "suggestion": "Contactá a soporte"}],
                "raw": [str(raw)]
            }

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
