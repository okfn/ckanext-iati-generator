from ckan import model
from ckan.plugins import toolkit
from ckanext.iati_generator.models.iati_files import IATIFile, DEFAULT_NAMESPACE
from ckanext.iati_generator.models.enums import IATIFileTypes


def _is_sysadmin(context):
    user_obj = context.get("auth_user_obj")
    return bool(user_obj and user_obj.sysadmin)


def _resolve_package_id_from_resource_id(resource_id):
    """Return package_id owning a given CKAN resource_id, or None."""
    if not resource_id:
        return None
    res = model.Resource.get(resource_id)
    return getattr(res, "package_id", None) if res else None


def _resolve_package_id_from_iati_file_id(file_id):
    """Return package_id from an IATIFile.id -> resource_id -> package_id chain, or None."""
    if not file_id:
        return None
    file = model.Session.query(IATIFile).get(file_id)
    if not file:
        return None
    return _resolve_package_id_from_resource_id(file.resource_id)


def _resolve_package_id(data_dict):
    """Return package_id from data_dict which may contain resource_id or IATIFile.id.
       1) resource_id  -> package_id (for create)
       2) id (IATIFile.id) -> resource_id -> package_id (for update or delete)
    """
    # 1) If an IATIFile id is provided (update/delete)
    pkg_id = _resolve_package_id_from_iati_file_id(data_dict.get("id"))
    if pkg_id:
        return pkg_id
    # 2) Fallback: resource_id (create or update/delete con solo resource_id)
    return _resolve_package_id_from_resource_id(data_dict.get("resource_id"))


def _user_is_org_admin_for_package(context, package_id):
    """
    Return True if the user is an admin of the organization that owns the dataset.
    Not to be confused with 'package_update' (which allows editors).
    """
    if not package_id:
        return False

    # owner_org of the dataset (no actions or permissions)
    pkg = model.Package.get(package_id)
    if not pkg or not pkg.owner_org:
        return False
    org_id = pkg.owner_org

    # user_id from the context
    user_name = context.get("user")
    user_obj = model.User.get(user_name) if user_name else None
    if not user_obj:
        return False

    # list the user's organizations and check their capacity
    user_orgs = toolkit.get_action("organization_list_for_user")(context, {"id": user_obj.id})
    return any(o.get("id") == org_id and o.get("capacity") == "admin" for o in user_orgs)


def _allow_if_sysadmin_or_org_admin(context, package_id):
    if _is_sysadmin(context):
        return {"success": True}

    if _user_is_org_admin_for_package(context, package_id):
        return {"success": True}

    return {
        "success": False,
        "msg": toolkit._("Only organization admins (or sysadmins) can perform this action."),
    }


def iati_file_create(context, data_dict):
    # org-admin del dataset (o sysadmin).
    # Expect only resource_id; resolve package_id from it.
    package_id = _resolve_package_id(data_dict)
    if not package_id:
        return {
            "success": False,
            "msg": toolkit._("Missing or invalid resource_id; cannot resolve dataset for IATI file creation."),
        }
    return _allow_if_sysadmin_or_org_admin(context, package_id)


def iati_file_update(context, data_dict):
    # Expect id (IATIFile.id); fallback to resource_id.
    package_id = _resolve_package_id(data_dict)
    if not package_id:
        return {
            "success": False,
            "msg": toolkit._("Cannot resolve dataset for IATI file update (need valid id or resource_id)."),
        }
    return _allow_if_sysadmin_or_org_admin(context, package_id)


def iati_file_delete(context, data_dict):
    # Expect id (IATIFile.id); fallback to resource_id.
    package_id = _resolve_package_id(data_dict)
    if not package_id:
        return {
            "success": False,
            "msg": toolkit._("Cannot resolve dataset for IATI file deletion (need valid id or resource_id)."),
        }
    return _allow_if_sysadmin_or_org_admin(context, package_id)


def iati_generate(context, data_dict):
    """
    Authorization for IATI generation.
    Only sysadmins can trigger IATI generation.
    """
    if _is_sysadmin(context):
        return {"success": True}

    return {
        "success": False,
        "msg": toolkit._("Only sysadmins can trigger IATI generation."),
    }


def iati_file_show(context, data_dict):
    # Unrestricted access
    return {"success": True}


def iati_file_list(context, data_dict):
    # Global listing: only sysadmins (API equivalent of the /ckan-admin/list-iati-files view)
    if _is_sysadmin(context):
        return {"success": True}
    return {
        "success": False,
        "msg": toolkit._("Only sysadmins can list IATI files.")
    }


def _resolve_package_id_from_final_org_file(namespace):
    """
    Look for the IATIFile with FINAL_ORGANIZATION_FILE for the given namespace
    and return its package_id (via resource_id), or None.
    """
    ns = namespace or DEFAULT_NAMESPACE

    session = model.Session
    iati_file = (
        session.query(IATIFile)
        .filter(IATIFile.namespace == ns)
        .filter(IATIFile.file_type == IATIFileTypes.FINAL_ORGANIZATION_FILE.value)
        .first()
    )
    if not iati_file:
        return None

    return _resolve_package_id_from_resource_id(iati_file.resource_id)


def generate_organization_xml(context, data_dict):
    """
    Authorization for generating organization XML.
    Only sysadmins or organization admins can generate XML for their organization.
    """
    namespace = data_dict.get("namespace") or DEFAULT_NAMESPACE
    package_id = _resolve_package_id_from_final_org_file(namespace)

    if not package_id:
        return {
            "success": False,
            "msg": toolkit._(
                "Cannot resolve dataset for organization XML generation "
                "(missing FINAL_ORGANIZATION_FILE for this namespace)."
            ),
        }

    return _allow_if_sysadmin_or_org_admin(context, package_id)
