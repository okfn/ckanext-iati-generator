import logging
from ckan.plugins import toolkit


log = logging.getLogger(__name__)


def iati_tab_enabled():
    val = toolkit.config.get("ckanext.iati_generator.hide_tab", "false")
    if not val:
        val = "false"
    bool_val = toolkit.asbool(val)
    return not bool_val


def _extras_as_dict(extras):
    """
    CKAN puede pasar extras como lista de {'key','value'} o como dict plano.
    Normaliza a dict.
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
    Helper seguro para leer un extra por clave.
    Se usa en la template para precargar valores.
    """
    try:
        data = _extras_as_dict(extras)
        return data.get(key, default) or default
    except Exception as e:
        log.warning("get_dict_value failed: %s", e)
        return default


def get_iati_file_reference_options():
    """
    Devuelve opciones para el select de 'IATI file reference' en formato:
    [{'value': '<valor_enum>', 'text': '<etiqueta>'}, ...]

    Intenta obtenerlas desde un enum local. Si no existe, hace fallback
    a una lista vacía (no rompe el render).
    """
    options = []
    try:
        # Ajustá el import al módulo real donde tengas el enum
        # Debe ser un Enum con miembros que tengan .value y .name (o .label)
        from ckanext.iati_generator.models.enums import IATIFileTypes
        for item in IATIFileTypes:
            value = getattr(item, "value", None) or str(item)
            # Etiqueta legible: usa .label si existe; si no, formatea el nombre
            text = getattr(item, "label", None) or item.name.replace("_", " ").title()
            options.append({"value": value, "text": text})

    except Exception as e:
        log.warning("IATI enum not found or failed (%s). Returning empty options.", e)
        # Si querés un fallback estático mientras tanto, descomenta y ajusta:
        # options = [
        #     {"value": "activities", "text": "Activities"},
        #     {"value": "transactions", "text": "Transactions"},
        # ]
    return options
