from flask import Blueprint
from sqlalchemy.orm import joinedload

from ckan.plugins import toolkit
from ckan import model as ckan_model
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
    # Collect IATI “file” rows from resources that define the IATI extras.
    # Expected extras:
    #   - iati_namespace (string)
    #   - iati_file_reference (enum value from IATIFileTypes)
    #   - iati_valid (bool-like "true"/"false")
    #   - iati_last_success (YYYY-MM-DD)
    #   - iati_last_error (YYYY-MM-DD)
    #   - iati_error_message (string)
    # Adjust keys if your naming differs.
    rows = []
    # Collect IATI “file” rows from resources that define the IATI extras.
    resources = (
        ckan_model.Session.query(ckan_model.Resource)
        .options(joinedload(ckan_model.Resource.package))
        .all()
    )
    for res in resources:
        extras = {}
        if hasattr(res, "extras") and isinstance(res.extras, dict):
            extras = res.extras or {}
        elif hasattr(res, "extras_list"):
            extras = {e.key: e.value for e in (res.extras_list or [])}
        file_ref = extras.get("iati_file_reference")
        if not file_ref:
            continue

        # Humanized “File type” from enum (fallback to raw)
        file_type = file_ref  # if you have an Enum mapping, convert here

        valid_str = (extras.get("iati_valid") or "").strip().lower()
        is_valid = valid_str in ("1", "true", "yes")

        last_success = (extras.get("iati_last_success") or "").strip()
        last_error = (extras.get("iati_last_error") or "").strip()
        error_msg = (extras.get("iati_error_message") or "").strip()

        notes = ""
        if is_valid and last_success:
            notes = f"Last success: {last_success}"
        elif not is_valid and last_error:
            notes = f"Last error: {last_error}"
            if error_msg:
                notes += f" – {error_msg}"

        rows.append({
            "file_type": file_type,
            "resource_name": res.name or res.id,
            "resource_id": res.id,
            "dataset_name": res.package.name if res.package else "",
            "valid": is_valid,
            "notes": notes
        })

    return toolkit.render(
        "iati/iati_files.html",
        {"iati_files": rows}
    )
