import logging
from flask import Blueprint, redirect
from ckan.plugins import toolkit
from ckanext.iati_generator.models.enums import IATIFileTypes

log = logging.getLogger(__name__)

iati_public = Blueprint("iati_public", __name__, url_prefix="/iati")


def _find_final_resource(dataset: dict, file_type_value: int):
    for res in dataset.get("resources", []):
        ft = res.get("iati_file_type")

        if not ft:
            for extra in res.get("extras", []):
                if extra.get("key") == "iati_file_type":
                    ft = extra.get("value")
                    break

        if not ft:
            continue

        if str(ft).isdigit() and int(ft) == file_type_value:
            return res.get("url")

    return None


@iati_public.route("/<namespace>/organisation.xml")
def public_org(namespace):
    ctx = {"ignore_auth": True, "user": ""}
    dataset = toolkit.get_action("iati_get_dataset_by_namespace")(ctx, {"namespace": namespace})

    if not dataset:
        return toolkit.abort(404, f"No dataset found for namespace: {namespace}")

    url = _find_final_resource(dataset, IATIFileTypes.FINAL_ORGANIZATION_FILE.value)
    if not url:
        return toolkit.abort(404, f"No organisation.xml found for namespace: {namespace}")

    return redirect(url, code=302)


@iati_public.route("/<namespace>/activity.xml")
def public_act(namespace):
    ctx = {"ignore_auth": True, "user": ""}
    dataset = toolkit.get_action("iati_get_dataset_by_namespace")(ctx, {"namespace": namespace})

    if not dataset:
        return toolkit.abort(404, f"No dataset found for namespace: {namespace}")

    url = _find_final_resource(dataset, IATIFileTypes.FINAL_ACTIVITY_FILE.value)
    if not url:
        return toolkit.abort(404, f"No activity.xml found for namespace: {namespace}")

    return redirect(url, code=302)
