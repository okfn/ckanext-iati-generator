from flask import Blueprint, request

from ckan.plugins import toolkit

from ckanext.iati_generator.decorators import require_sysadmin_user


iati_file_admin = Blueprint("iati_generator_admin_files", __name__, url_prefix="/ckan-admin/list-iati-files")


@iati_file_admin.route("/iati-files")
@require_sysadmin_user
def iati_files_index():
    """List all IATI “files” (resources with IATI extras) in the system.
    This is a simple admin view to see the status of IATI files.
    """
    context = {"user": toolkit.c.user}
    start = int(request.args.get("start", 0) or 0)
    page_size = int(request.args.get("rows", 100) or 100)
    namespace = request.args.get("namespace")

    params = {"start": start, "rows": page_size}

    # namespace filter
    if namespace:
        params["namespace"] = namespace
    data = toolkit.get_action("iati_resources_list")(context, params)

    rows_out = []
    for item in data.get("results", []):
        resource = item.get("resource") or {}
        dataset = item.get("dataset") or {}
        iati_file = item.get("iati_file") or {}

        res_id = resource.get("id")
        pkg_name = dataset.get("name", "")

        # generate resource URL
        res_url = f"/dataset/{pkg_name}/resource/{res_id}" if pkg_name and res_id else "#"

        # Validation info
        is_valid = bool(iati_file.get("is_valid"))
        last_success = iati_file.get("last_processed_success")
        last_error = iati_file.get("last_error") or ""

        if is_valid and last_success:
            notes = f"Last success: {last_success}"
        elif not is_valid and last_error:
            notes = f"Last error: {last_error}"
        else:
            notes = ""

        # Append row
        rows_out.append({
            "namespace": iati_file.get("namespace", ""),
            "file_type": iati_file.get("file_type", ""),
            "resource_name": resource.get("name") or res_id,
            "resource_id": res_id,
            "dataset_name": pkg_name,
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
            "namespace": namespace or "",
        },
    )


@iati_file_admin.route("/generate", methods=["POST"])
@require_sysadmin_user
def generate_iati():
    """
    Generate IATI files for a given namespace and file category.
    """

    context = {"user": toolkit.c.user}

    namespace = request.form.get("namespace")
    file_category = request.form.get("file_category", "organization")

    if not namespace:
        toolkit.h.flash_error(toolkit._("Namespace is required"))
        return toolkit.redirect_to("iati_generator_admin_files.iati_files_index")

    try:
        result = toolkit.get_action("iati_generate")(context, {
            "namespace": namespace,
            "file_category": file_category
        })

        toolkit.h.flash_success(result.get('message'))
    except toolkit.ValidationError as e:
        for field, errors in e.error_dict.items():
            toolkit.h.flash_error(f"{field}: {errors}")
    except Exception as e:
        toolkit.h.flash_error(toolkit._(f"Error generating IATI files: {str(e)}"))

    return toolkit.redirect_to("iati_generator_admin_files.iati_files_index", namespace=namespace)
