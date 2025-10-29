from ckan import model
from ckan.plugins import toolkit


IATI_EXTRA_KEYS = {"iati_namespace", "iati_file_type"}


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


def _resource_show(context, rid):
    try:
        return toolkit.get_action("resource_show")(context, {"id": rid})
    except Exception:
        return {}


def _get_existing_value(res_dict, field_name):
    # CKAN guarda campos scheming de recurso como atributos directos si están mapeados
    if field_name in res_dict:
        return res_dict.get(field_name)
    # fallback: buscar en extras
    for it in res_dict.get("extras", []):
        if it.get("key") == field_name:
            return it.get("value")
    return None


def iati_protect_org_admin_only(key, data, errors, context):
    """
    Validator to protect IATI extra fields so that only org admins (or sysadmins)
    can set or modify them.
    If the user is not authorized, the existing value is restored (or removed on create).
    """

    field_name = key[0] if isinstance(key, tuple) and key else key
    if field_name not in IATI_EXTRA_KEYS:
        return

    res_id = data.get(('id',)) or data.get('id')
    if not res_id:
        # CREATE: check using package_id from payload
        pkg_id = data.get(('package_id',)) or data.get('package_id') \
                 or data.get(('dataset_id',)) or data.get('dataset_id')
        if not _user_is_org_admin_for_package(context, pkg_id):
            # discard the incoming value if the user is not an org admin
            data.pop(key, None)
        return

    # UPDATE: check using the resource's package
    current_res = _resource_show(context, res_id)
    package_id = current_res.get("package_id")
    if _user_is_org_admin_for_package(context, package_id):
        return
    # not authorized: restore existing value
    existing = _get_existing_value(current_res, field_name)
    if existing is not None:
        data[key] = existing
