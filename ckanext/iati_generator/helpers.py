import logging
from ckan.plugins import toolkit
from ckanext.iati_generator.models.enums import IATIFileTypes


log = logging.getLogger(__name__)


def iati_tab_enabled():
    val = toolkit.config.get("ckanext.iati_generator.hide_tab", "false")
    if not val:
        val = "false"
    bool_val = toolkit.asbool(val)
    return not bool_val


def iati_file_types(field):
    """
    Returns options (value/label) for the Scheming select.
    Scheming calls with `field`, although we don't use it.
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
