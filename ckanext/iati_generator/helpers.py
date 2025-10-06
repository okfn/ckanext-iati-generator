from ckan.plugins import toolkit
from ckanext.iati_generator.models.enums import IATIFileTypes

def iati_tab_enabled():
    val = toolkit.config.get("ckanext.iati_generator.hide_tab", "false")
    if not val:
        val = "false"
    bool_val = toolkit.asbool(val)
    return not bool_val


def get_iati_file_reference_options():
    """
    Devuelve opciones para el <select> de 'IATI file reference'.
    Basadas en el Enum IatiFileReferenceEnum.
    """
    return [
        {
            "value": str(e.value),
            "text": e.name.replace("_", " ").title()
        }
        for e in IATIFileTypes
    ]