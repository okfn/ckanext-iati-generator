import logging
from ckan.plugins import toolkit
from ckan import model as ckan_model
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.models.iati_files import IATIFile


log = logging.getLogger(__name__)


_FILENAME_BY_TYPE = {
    IATIFileTypes.ORGANIZATION_MAIN_FILE.value: "organization.xml",
    # IATIFileTypes.ACTIVITY_MAIN_FILE.value: "activities.xml",
    # if you later add more types, add them here
}


def iati_tab_enabled():
    val = toolkit.config.get("ckanext.iati_generator.hide_tab", "false")
    if not val:
        val = "false"
    bool_val = toolkit.asbool(val)
    return not bool_val


def iati_file_types(field=None):
    """
    Returns options (value/label) for the Scheming select.
    We plan to use this in the schema file, like "choices_helper: iati_file_types".
    So the Scheming extension call this helper with `field`, although we don't use it.
    """
    options = []
    # optional: sorted by value
    for item in sorted(IATIFileTypes, key=lambda e: e.value):
        label = item.name.replace("_", " ").title()
        options.append({
            "value": str(item.value),  # Scheming expects a string
            "label": label,
        })
    return options


def build_public_iati_links_namespace(namespace):
    """
    Builds a list of public IATI file links for a given namespace.
    This function is actively used to collect all active resources for a given namespace across the instance,
    ignoring package_id, and returns the same structure as the package-scoped helper.

    Returns:
      List[dict] like:
        {
          "label": "<namespace> – <filename>",
          "url": "/iati/<namespace>/<filename>",
          "status": "valid" | "error",
          "resource_id": "<resource-id>"
        }
    """
    Session = ckan_model.Session
    Resource = ckan_model.Resource

    q = (
        Session.query(IATIFile, Resource)
        .join(Resource, Resource.id == IATIFile.resource_id)
        .filter(IATIFile.namespace == namespace, Resource.state == "active")
    )

    items = []
    for f, res in q.all():
        filename = _FILENAME_BY_TYPE.get(f.file_type)
        if not filename:
            continue
        items.append({
            "label": f"{f.namespace} – {filename}",
            "url": f"/iati/{f.namespace}/{filename}",
            "status": "valid" if f.is_valid else "error",
            "resource_id": f.resource_id,
        })

    items.sort(key=lambda x: (x["label"], x["resource_id"]))
    return items
