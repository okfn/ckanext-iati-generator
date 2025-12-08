from flask import Blueprint, redirect
from ckan.plugins import toolkit
from ckan import model
from ckanext.iati_generator.models.iati_files import IATIFile
from ckanext.iati_generator.models.enums import IATIFileTypes
from sqlalchemy import and_

iati_public = Blueprint("iati_public", __name__, url_prefix="/iati")


def _find_latest_resource_url(namespace, file_type):
    """
    Docstring for _find_latest_resource_url

    :param namespace: Description
    :param file_type: Description
    """
    Session = model.Session
    q = (
        Session.query(IATIFile)
        .filter(
            and_(
                IATIFile.namespace == namespace,
                IATIFile.file_type == file_type,
                IATIFile.is_valid.is_(True),
            )
        )
        .order_by(IATIFile.last_processed_success.desc())
        .first()
    )

    # No valid file found
    if not q:
        return None

    # get full CKAN resource dict
    context = {"ignore_auth": True}
    res_dict = toolkit.get_action("resource_show")(context, {"id": q.resource_id})

    return res_dict.get("url")


@iati_public.route("/<namespace>/organization.xml")
def public_org(namespace):
    """
    Public endpoint to serve the latest valid organization XML file for a given namespace.

    :param namespace: The namespace identifier for the IATI organization.
    """
    url = _find_latest_resource_url(namespace, IATIFileTypes.ORGANIZATION_MAIN_FILE.value)
    if not url:
        return toolkit.abort(404, f"No organization XML for namespace: {namespace}")
    return redirect(url, code=302)


@iati_public.route("/<namespace>/activities.xml")
def public_act(namespace):
    """
    Public endpoint to serve the latest valid activities XML file for a given namespace.

    :param namespace: The namespace identifier for the IATI activities.
    """
    url = _find_latest_resource_url(namespace, IATIFileTypes.ACTIVITY_MAIN_FILE.value)
    if not url:
        return toolkit.abort(404, f"No activities XML for namespace: {namespace}")
    return redirect(url, code=302)
