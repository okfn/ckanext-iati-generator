from flask import Blueprint

from ckan.plugins import toolkit
from ckan import model as ckan_model
from ckanext.iati_generator.decorators import require_sysadmin_user
from ckanext.iati_generator.actions.iati import list_datasets_with_iati
from ckanext.iati_generator.models.iati_files import IATIFile
from ckanext.iati_generator.models.enums import IATIFileTypes

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

    q = (
        Session.query(
            IATIFile.id.label("iati_id"),
            IATIFile.namespace.label("namespace"),
            IATIFile.file_type.label("file_type"),
            IATIFile.is_valid.label("is_valid"),
            IATIFile.last_processed_success.label("last_success"),
            IATIFile.last_error.label("error_message"),

            Resource.id.label("resource_id"),
            Resource.name.label("resource_name"),
            Resource.url.label("resource_url"),
            Resource.format.label("resource_format"),
            Resource.description.label("resource_description"),

            Package.name.label("package_name"),
        )
        .join(Resource, Resource.id == IATIFile.resource_id)
        .join(Package, Resource.package_id == Package.id)
        .filter(Resource.state == "active", Package.state == "active")
        .order_by(Package.name.asc(), Resource.name.asc())
    )

    rows = []
    for r in q.all():
        # Mapear el file_type (int) al nombre del Enum, con fallback seguro
        try:
            file_type_label = IATIFileTypes(r.file_type).name
        except Exception:
            file_type_label = str(r.file_type or "")

        is_valid = bool(r.is_valid)

        notes = ""
        if is_valid and r.last_success:
            notes = f"Last success: {r.last_success}"
        elif not is_valid and (r.error_message or ""):
            notes = f"Last error: {r.error_message}"

        rows.append({
            "file_type": file_type_label,
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
