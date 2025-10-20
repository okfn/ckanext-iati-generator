from ckan import model
from ckan.plugins import toolkit


def _is_sysadmin(context):
    user_obj = context.get("auth_user_obj")
    return bool(user_obj and user_obj.sysadmin)


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
    # org-admin del dataset (o sysadmin)
    package_id = data_dict.get("package_id") or data_dict.get("dataset_id")
    return _allow_if_sysadmin_or_org_admin(context, package_id)


def iati_file_update(context, data_dict):
    package_id = data_dict.get("package_id") or data_dict.get("dataset_id")
    return _allow_if_sysadmin_or_org_admin(context, package_id)


def iati_file_delete(context, data_dict):
    package_id = data_dict.get("package_id") or data_dict.get("dataset_id")
    return _allow_if_sysadmin_or_org_admin(context, package_id)


def iati_file_show(context, data_dict):
    # mostrar no restringido
    return {"success": True}
