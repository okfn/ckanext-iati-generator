"""
Override the resources_create and resources_update actions to
handle IATI file extras.
"""

import logging

from ckan import model
from ckan.plugins import toolkit

from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE, IATIFile

log = logging.getLogger(__name__)


def iati_resource_show(context, data_dict):
    """Enrichs the resource dict with IATI File Metadata."""
    resource_id = data_dict["id"]

    iati_file = model.Session.query(IATIFile).filter_by(resource_id=resource_id).first()
    if not iati_file:
        return data_dict

    data_dict["iati_is_valid"] = iati_file.is_valid
    data_dict["iati_last_error"] = iati_file.last_error

    return data_dict


def iati_resource_create(context, data_dict):
    """Creates an IATI File upon resource creation."""
    iati_file_type = data_dict.get("iati_file_type", None)
    if not iati_file_type:
        return
    pkg_dict = toolkit.get_action("package_show")({}, {"id": data_dict["package_id"]})
    namespace = pkg_dict.get("iati_namespace")
    if not namespace:
        namespace = DEFAULT_NAMESPACE

    toolkit.get_action('iati_file_create')({}, {
        "resource_id": data_dict["id"],
        "namespace": namespace,
        "file_type": iati_file_type,
    })


def iati_resource_update(context, data_dict):
    """Updates an IATI File upon resource update."""
    res_id = data_dict['id']
    existing = model.Session.query(IATIFile).filter_by(resource_id=res_id).first()

    if not existing:
        iati_resource_create(context, data_dict)
        return

    iati_file_type = data_dict.get("iati_file_type", None)
    if not iati_file_type and existing:
        toolkit.get_action("iati_file_delete")({},{"id": existing.id})
        return

    pkg_dict = toolkit.get_action("package_show")({}, {"id": data_dict["package_id"]})
    namespace = pkg_dict.get("iati_namespace")
    if not namespace:
        namespace = DEFAULT_NAMESPACE

    file_dict = { "id": existing.id, "file_type": iati_file_type, "namespace": namespace }
    toolkit.get_action("iati_file_update")({},file_dict)


@toolkit.side_effect_free
@toolkit.chained_action
def resource_show(up_function, context, data_dict):
    resource = up_function(context, data_dict)
    resource = iati_resource_show(context, resource)
    return resource


@toolkit.chained_action
def resource_create(up_function, context, data_dict):
    resource = up_function(context, data_dict)
    iati_resource_create(context, resource)
    return resource


@toolkit.chained_action
def resource_update(up_function, context, data_dict):
    resource = up_function(context, data_dict)
    iati_resource_update(context, resource)
    return resource
