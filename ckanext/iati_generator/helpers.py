import logging
from ckan import model
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE, IATIFile


log = logging.getLogger(__name__)


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


# ===========================================================================
# Helpers para mapear recursos <-> IATIFile y extras
# ===========================================================================


def iati_files_by_resource():
    """
    Returns an index {resource_id: IATIFile} to allow simple
    validation status queries.
    """
    session = model.Session
    files = session.query(IATIFile).all()
    return {f.resource_id: f for f in files}


def extract_file_type_from_resource(res):
    """
    Returns (file_type_int, label) from the resource.
    If there's no file_type, returns (None, None).
    """
    file_type = res.get("iati_file_type")

    if not file_type:
        for extra in res.get("extras", []):
            if extra.get("key") == "iati_file_type":
                file_type = extra.get("value")
                break

    if not file_type:
        return None, None

    # Try as integer
    try:
        ft_int = int(file_type)
        return ft_int, IATIFileTypes(ft_int).name
    except Exception:
        pass

    # Try as Enum name
    try:
        enum_member = IATIFileTypes[file_type]
        return enum_member.value, enum_member.name
    except Exception:
        # Last resort: leave the label as is (without enum mapping)
        return None, file_type


def extract_namespace_from_resource(res):
    """
    Gets the namespace from the resource or its extras.
    If not found, returns DEFAULT_NAMESPACE.
    """
    ns = res.get("iati_namespace")
    if ns:
        return ns

    for extra in res.get("extras", []):
        if extra.get("key") == "iati_namespace":
            return extra.get("value")

    return DEFAULT_NAMESPACE


# Candidates

def normalize_file_type(file_type):
    """
    UI-friendly parser for file_type values.

    Returns:
        (label, ft_int):
          - label: human-readable label (enum name or original value)
          - ft_int: integer enum value (or None if unknown)

    Unlike actions._normalize_file_type, this helper:
      - never raises ValidationError
      - accepts unknown values and just returns (original_value, None)
    """
    if file_type is None:
        return None, None

    label = file_type
    ft_int = None
    try:
        ft_int = int(file_type)
        label = IATIFileTypes(ft_int).name
    except Exception:
        # tal vez venga como nombre del enum
        try:
            ft_int = IATIFileTypes[file_type].value
        except Exception:
            pass
    return label, ft_int
