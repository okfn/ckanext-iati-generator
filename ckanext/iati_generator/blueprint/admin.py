from flask import Blueprint
from sqlalchemy.orm import aliased
from sqlalchemy import and_

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
    Session = ckan_model.Session
    Resource = ckan_model.Resource
    Package = ckan_model.Package
    ResourceExtra = ckan_model.ResourceExtra

    # Aliases for each resource extra we want to read
    re_file_ref = aliased(ResourceExtra)
    re_namespace = aliased(ResourceExtra)
    re_valid = aliased(ResourceExtra)
    re_last_success = aliased(ResourceExtra)
    re_last_error = aliased(ResourceExtra)
    re_error_message = aliased(ResourceExtra)

    q = (
        Session.query(
            Resource.id.label("resource_id"),
            Resource.name.label("resource_name"),
            Package.name.label("package_name"),
            re_file_ref.value.label("file_type"),
            re_namespace.value.label("namespace"),
            re_valid.value.label("valid"),
            re_last_success.value.label("last_success"),
            re_last_error.value.label("last_error"),
            re_error_message.value.label("error_message"),
        )
        .join(Package, Resource.package_id == Package.id)
        .filter(Resource.state == 'active')
        .filter(Package.state == 'active')
        # Only include resources that have iati_file_reference
        .join(
            re_file_ref,
            and_(re_file_ref.resource_id == Resource.id,
                 re_file_ref.key == "iati_file_reference"),
        )
        # Optional extras (use outerjoin)
        .outerjoin(
            re_namespace,
            and_(re_namespace.resource_id == Resource.id,
                 re_namespace.key == "iati_namespace"),
        )
        .outerjoin(
            re_valid,
            and_(re_valid.resource_id == Resource.id,
                 re_valid.key == "iati_valid"),
        )
        .outerjoin(
            re_last_success,
            and_(re_last_success.resource_id == Resource.id,
                 re_last_success.key == "iati_last_success"),
        )
        .outerjoin(
            re_last_error,
            and_(re_last_error.resource_id == Resource.id,
                 re_last_error.key == "iati_last_error"),
        )
        .outerjoin(
            re_error_message,
            and_(re_error_message.resource_id == Resource.id,
                 re_error_message.key == "iati_error_message"),
        )
        .order_by(Package.name.asc(), Resource.name.asc())
    )

    rows = []
    for r in q.all():
        valid_str = (r.valid or "").strip().lower()
        is_valid = valid_str in ("1", "true", "yes")

        notes = ""
        if is_valid and (r.last_success or "").strip():
            notes = f"Last success: {r.last_success.strip()}"
        elif not is_valid and (r.last_error or "").strip():
            notes = f"Last error: {r.last_error.strip()}"
            if (r.error_message or "").strip():
                notes += f" – {r.error_message.strip()}"

        rows.append({
            "file_type": r.file_type or "",
            "resource_name": r.resource_name or r.resource_id,
            "resource_id": r.resource_id,
            "dataset_name": r.package_name or "",
            "valid": is_valid,
            "notes": notes,
        })

    return toolkit.render(
        "iati/iati_files.html",
        {"iati_files": rows}
    )
