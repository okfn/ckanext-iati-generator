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

def build_iati_index():
    """
    Build an in-memory index of IATIFile by (resource_id, namespace, file_type).
    """
    Session = model.Session
    files = Session.query(IATIFile).all()
    index = {}
    for f in files:
        key = (f.resource_id, f.namespace, f.file_type)
        index[key] = f
    return index


def normalize_file_type(file_type):
    """
    Return (label, ft_int) for a raw file_type value.
    label: human readable (enum name or original value)
    ft_int: integer enum value (or None if unknown)
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


def build_candidate_row(pkg, res, label, ns, ft_int, iati_index):
    """
    Build the output dict for a single candidate resource, including validation.
    """
    iati_file = None
    if ft_int is not None:
        iati_file = iati_index.get((res["id"], ns, ft_int))

    is_valid = bool(iati_file.is_valid) if iati_file else False
    last_success = (
        iati_file.last_processed_success.isoformat()
        if iati_file and iati_file.last_processed_success
        else None
    )
    last_error = iati_file.last_error if iati_file else None

    return {
        "namespace": ns,
        "file_type": label,
        "is_valid": is_valid,
        "last_success": last_success,
        "last_error": last_error,
        "resource": {
            "id": res["id"],
            "name": res.get("name") or res["id"],
            "format": res.get("format"),
            "url": res.get("url"),
            "description": res.get("description"),
        },
        "dataset": {
            "id": pkg["id"],
            "name": pkg["name"],
            "title": pkg["title"],
            "owner_org": pkg["owner_org"],
        },
    }
