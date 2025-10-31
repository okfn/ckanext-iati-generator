from ckan import model
from ckan.plugins import toolkit
from ckanext.iati_generator.models.iati_files import IATIFile


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
    # 2) Fallback: resource_id (create o update/delete con solo resource_id)
    return _resolve_package_id_from_resource_id(data_dict.get("resource_id"))


def _user_is_org_admin_for_package(context, package_id):
    """
    Return True if the user is an admin of the organization that owns the dataset.
    Not to be confused with 'package_update' (which allows editors).
    """
    if not package_id:
        return False

    # owner_org del dataset (sin acciones ni permisos)
    pkg = model.Package.get(package_id)
    if not pkg or not pkg.owner_org:
        return False
    org_id = pkg.owner_org

    # user_id desde el contexto
    user_name = context.get("user")
    user_obj = model.User.get(user_name) if user_name else None
    if not user_obj:
        return False

    # listar organizaciones del usuario y chequear capacity
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


def iati_file_show(context, data_dict):
    # Unrestricted access
    return {"success": True}
