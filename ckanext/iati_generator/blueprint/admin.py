from ckan.plugins import toolkit
from flask import Blueprint, request

from ckanext.iati_generator import helpers as h
from ckanext.iati_generator.decorators import require_sysadmin_user
from ckanext.iati_generator.models.enums import IATIFileTypes

iati_file_admin = Blueprint("iati_generator_admin_files", __name__, url_prefix="/ckan-admin/list-iati-files")


def _get_iati_display_name(code):
    name = ""
    try:
        name = IATIFileTypes(int(code)).name
    except ValueError:
        name = "Wrong code name"
    return name.replace("_", " ").title()


@iati_file_admin.route("/iati-files")
@require_sysadmin_user
def iati_files_index():
    """List IATI files and missing files for the selected dataset."""
    search = toolkit.get_action('package_search')({}, {'fq': 'iati_namespace:[* TO *]'})
    iati_datasets = [dataset for dataset in search.get("results", [])]
    package_id = request.args.get("package_id")
    if not package_id:
        return toolkit.render("iati/iati_files.html", {
            "package_id": "",
            "iati_datasets": iati_datasets,
            "pending_files": {"organization": [], "activity": []}
        })

    dataset = toolkit.get_action('package_show')({}, {"id": package_id})

    rows_out = []
    for resource in dataset["resources"]:
        url = toolkit.url_for("resource.read", package_type=dataset["type"], id=dataset["id"], resource_id=resource["id"])
        rows_out.append({
            "file_type": _get_iati_display_name(resource.get("iati_file_type")),
            "resource_name": resource.get("name") or resource.get("id"),
            "resource_url": url,
        })

    pending_files = h.get_pending_mandatory_files(dataset["id"])

    return toolkit.render(
        "iati/iati_files.html",
        {
            "iati_datasets": iati_datasets,
            "package_id": package_id,
            "iati_files": rows_out,
            "pending_files": pending_files,
        },
    )
