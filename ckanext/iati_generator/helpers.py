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


def iati_file_type():
    """
    Returns options for the 'IATI file type' select in the format:
    [{'value': '<enum_value>', 'text': '<label>'}, ...]
    """
    return [
        {
            "value": getattr(item, "value", str(item)),
            "text": getattr(item, "label", None) or item.name.replace("_", " ").title(),
        }
        for item in IATIFileTypes
    ]
