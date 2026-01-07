"""
Override the resources_create and resources_update actions to
handle IATI file extras.
"""
from os import name
from ckan.tests.lib.navl.test_dictization_functions import data

import logging

from ckan.plugins import toolkit
from ckan import model

from ckanext.iati_generator import helpers as h
from ckanext.iati_generator.models.iati_files import IATIFile, DEFAULT_NAMESPACE

log = logging.getLogger(__name__)


def _sync_iati_file_for_resource(context, resource_dict):
    """
    Creates / updates / deletes the IATIFile associated with the resource based on
    the iati_file_type / iati_namespace extras of the resource.
    """
    res_id = resource_dict.get("id")
    if not res_id:
        return

    # Read type and namespace from the resource (uses existing helpers)
    file_type_int, _label = h.extract_file_type_from_resource(resource_dict)
    namespace = h.extract_namespace_from_resource(resource_dict)

    session = model.Session
    existing = session.query(IATIFile).filter_by(resource_id=res_id).first()

    # If there's NO IATI type => if IATIFile exists, try to delete it
    if file_type_int is None:
        if existing:
            try:
                toolkit.get_action("iati_file_delete")(context, {"id": existing.id})
            except toolkit.NotAuthorized:
                log.warning(
                    "User %s not allowed to delete IATIFile %s",
                    context.get("user"), existing.id
                )
        return

    # If there's IATI type => create or update IATIFile using our actions
    payload = {
        "resource_id": res_id,
        "file_type": file_type_int,  # int from the IATIFileTypes enum
        "namespace": namespace,
    }

    action_name = "iati_file_update" if existing else "iati_file_create"
    if existing:
        payload["id"] = existing.id

    try:
        toolkit.get_action(action_name)(context, payload)
    except toolkit.NotAuthorized:
        # Respects the policy: only org-admin or sysadmin can create/edit IATIFile
        log.warning(
            "User %s not allowed to %s for resource %s",
            context.get("user"), action_name, res_id
        )
    except toolkit.ValidationError as e:
        log.error(
            "Validation error syncing IATIFile for resource %s: %r",
            res_id, getattr(e, "error_dict", e)
        )


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
