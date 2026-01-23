import logging
from flask import Blueprint, redirect
from ckan.plugins import toolkit
from ckan import model
from ckanext.iati_generator import helpers as h
from ckanext.iati_generator.models.enums import IATIFileTypes

log = logging.getLogger(__name__)

iati_public = Blueprint("iati_public", __name__, url_prefix="/iati")


def _dataset_for_namespace(namespace: str):
    session = model.Session

    try:
        packages = session.query(model.Package).filter(
            model.Package.state == 'active'
        ).all()

        log.debug("Searching for namespace=%r among %d active packages", namespace, len(packages))

        for pkg in packages:
            try:
                ctx = {"ignore_auth": True, "user": ""}
                dataset = toolkit.get_action("package_show")(ctx, {"id": pkg.id})

                dataset_ns = dataset.get("iati_namespace", "")
                if not dataset_ns:
                    for extra in dataset.get("extras", []):
                        if extra.get("key") == "iati_namespace":
                            dataset_ns = extra.get("value", "")
                            break

                if dataset_ns and (
                    dataset_ns == namespace or
                    dataset_ns == h.normalize_namespace(namespace) or
                    h.normalize_namespace(dataset_ns) == h.normalize_namespace(namespace)
                ):
                    log.info("Found dataset %r for namespace=%r", pkg.name, namespace)
                    return dataset

            except Exception as e:
                log.warning("Error getting package %r: %s", pkg.name, str(e))
                continue

        log.warning("No dataset found for namespace=%r", namespace)

    except Exception as e:
        log.error("Error in _dataset_for_namespace: %s", str(e), exc_info=True)

    return None


def _find_final_resource(dataset: dict, file_type_value: int):
    for res in dataset.get("resources", []):
        ft = res.get("iati_file_type")

        if ft:
            try:
                if int(ft) == file_type_value:
                    url = res.get("url")
                    log.info("Found resource %r (type=%d) in dataset %r",
                             res.get("name"), file_type_value, dataset.get("name"))
                    return url
            except (ValueError, TypeError):
                continue

    log.warning("No resource with file_type=%d found in dataset %r",
                file_type_value, dataset.get("name"))
    return None


@iati_public.route("/<namespace>/organisation.xml")
def public_org(namespace):
    dataset = _dataset_for_namespace(namespace)
    if not dataset:
        return toolkit.abort(404, f"No dataset found for namespace: {namespace}")

    url = _find_final_resource(dataset, IATIFileTypes.FINAL_ORGANIZATION_FILE.value)
    if not url:
        return toolkit.abort(404, f"No organisation.xml found for namespace: {namespace}")

    return redirect(url, code=302)


@iati_public.route("/<namespace>/activity.xml")
def public_act(namespace):
    dataset = _dataset_for_namespace(namespace)
    if not dataset:
        return toolkit.abort(404, f"No dataset found for namespace: {namespace}")

    url = _find_final_resource(dataset, IATIFileTypes.FINAL_ACTIVITY_FILE.value)
    if not url:
        return toolkit.abort(404, f"No activity.xml found for namespace: {namespace}")

    return redirect(url, code=302)
