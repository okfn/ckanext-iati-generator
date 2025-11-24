from flask import Blueprint, request

from ckan.plugins import toolkit

from ckanext.iati_generator.decorators import require_sysadmin_user
from ckanext.iati_generator.actions.iati import list_datasets_with_iati

iati_blueprint_admin = Blueprint("iati_generator_admin", __name__, url_prefix="/ckan-admin/iati")
iati_file_admin = Blueprint("iati_generator_admin_files", __name__, url_prefix="/ckan-admin/list-iati-files")


@iati_blueprint_admin.route("/", methods=["GET"])
@require_sysadmin_user
def index():
    context = {"user": toolkit.c.user}
    datasets = list_datasets_with_iati(context)
    return toolkit.render("iati/admin.html", {"datasets": datasets})


@iati_file_admin.route("/iati-files")
@require_sysadmin_user
def iati_files_index():
    """List all IATI “files” (resources with IATI extras) in the system.
    This is a simple admin view to see the status of IATI files.
    """
    context = {"user": toolkit.c.user}
    start = int(request.args.get("start", 0) or 0)
    page_size = int(request.args.get("rows", 100) or 100)

    params = {"start": start, "rows": page_size}
    data = toolkit.get_action("iati_resources_list")(context, params)

    rows_out = []
    for item in data.get("results", []):
        resource = (item.get("resource") or {})
        dataset = (item.get("dataset") or {})
        res_id = resource.get("id")
        pkg_name = dataset.get("name", "")

        # Generate direct URL to the resource
        res_url = f"/dataset/{pkg_name}/resource/{res_id}" if pkg_name and res_id else "#"

        is_valid = bool(item.get("is_valid"))
        last_success = item.get("last_success")
        last_error = item.get("last_error") or ""

        if is_valid and last_success:
            notes = f"Last success: {last_success}"
        elif not is_valid and last_error:
            notes = f"Last error: {last_error}"
        else:
            notes = ""

        rows_out.append({
            "file_type": item.get("file_type", ""),
            "resource_name": (item.get("resource", {}) or {}).get("name") or (item.get("resource", {}) or {}).get("id"),
            "resource_id": (item.get("resource", {}) or {}).get("id"),
            "dataset_name": (item.get("dataset", {}) or {}).get("name", ""),
            "valid": is_valid,
            "notes": notes,
            "resource_url": res_url,
        })

    return toolkit.render(
        "iati/iati_files.html",
        {
            "iati_files": rows_out,
            "total": data.get("count", 0),
            "start": start,
            "rows": page_size,
        },
    )
