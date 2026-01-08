from ckan.plugins import toolkit
from flask import Blueprint, request

from ckanext.iati_generator.decorators import require_sysadmin_user

iati_file_admin = Blueprint("iati_generator_admin_files", __name__, url_prefix="/ckan-admin/list-iati-files")


@iati_file_admin.route("/iati-files")
@require_sysadmin_user
def iati_files_index():
    """List all IATI “files” (resources with IATI extras) in the system.
    This is a simple admin view to see the status of IATI files.
    """
    namespace = request.args.get("namespace")
    params = {}
    search_filter = "iati_namespace:[* TO *]"  # Get all datasets with namespace

    # namespace filter
    if namespace:
        params["namespace"] = namespace
        search_filter = f"iati_namespace:{namespace}"

    results = toolkit.get_action('package_search')({}, {'fq': search_filter})

    rows_out = []
    for dataset in results.get("results", []):
        for res in dataset["resources"]:
            # Call resource show to add IATI File fields to each resource dict.
            resource = toolkit.get_action("resource_show")({}, {"id": res["id"]})
            rows_out.append({
                "namespace": dataset.get("iati_namespace"),
                "file_type": resource.get("iati_file_type"),
                "resource_name": resource.get("name") or resource.get("id"),
                "resource_id": resource.get("id"),
                "dataset_name": dataset.get("name"),
                "valid": resource.get("iati_is_valid"),
                "notes": "Notes from the backend...",
                "resource_url": resource.get("url"),
            })

    return toolkit.render(
        "iati/iati_files.html",
        {
            "iati_files": rows_out,
            "total": results.get("count", 0),
            "namespace": namespace or "",
        },
    )
