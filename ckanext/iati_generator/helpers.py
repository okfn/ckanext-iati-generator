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


def _extras_as_dict(extras):
    """
    CKAN may pass extras as a list of {'key','value'} or as a plain dict.
    Normalizes to dict.
    """
    if isinstance(extras, dict):
        return extras
    if isinstance(extras, (list, tuple)):
        out = {}
        for item in extras:
            k = item.get('key') if isinstance(item, dict) else None
            v = item.get('value') if isinstance(item, dict) else None
            if k is not None:
                out[k] = v
        return out
    return {}


def get_dict_value(extras, key, default=""):
    """
    Safe helper to read an extra by key.
    Used in the template to preload values.
    """
    try:
        data = _extras_as_dict(extras)
        return data.get(key, default) or default
    except Exception as e:
        log.warning("get_dict_value failed: %s", e)
        return default


def get_iati_file_reference_options():
    """
    Return options for the 'IATI file reference' select in the format:
    [{'value': '<enum_value>', 'text': '<label>'}, ...]
    """
    return [
        {
            "value": getattr(item, "value", str(item)),
            "text": getattr(item, "label", None) or item.name.replace("_", " ").title(),
        }
        for item in IATIFileTypes
    ]
