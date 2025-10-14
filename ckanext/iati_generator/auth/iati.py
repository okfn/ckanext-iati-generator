

def iati_file_create(context, data_dict):
    """Only sysadmins are allowed"""
    user_obj = context.get("auth_user_obj")
    return {"success": user_obj.sysadmin}


def iati_file_update(context, data_dict):
    """Only sysadmins are allowed"""
    user_obj = context.get("auth_user_obj")
    return {"success": user_obj.sysadmin}


def iati_file_delete(context, data_dict):
    """Only sysadmins are allowed"""
    user_obj = context.get("auth_user_obj")
    return {"success": user_obj.sysadmin}


def iati_file_show(context, data_dict):
    return {"success": True}
