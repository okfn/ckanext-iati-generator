import logging
from ckan.plugins import toolkit
from ckan import model
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE, IATIFile


log = logging.getLogger(__name__)


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


def get_required_fields_by_file_type(file_type_enum):
    """
    Returns a list of required CSV fields based on the IATI file type.
    """
    if file_type_enum == IATIFileTypes.ORGANIZATION_MAIN_FILE:
        return [
            "organisation_identifier",
            "name",
            "reporting_org_ref",
            "reporting_org_type",
            "reporting_org_name",
            "reporting_org_lang",
            "default_currency",
            "xml_lang",
        ]
    elif file_type_enum == IATIFileTypes.ORGANIZATION_NAMES_FILE:
        return [
            "organisation_identifier",
            "language",
            "name",
        ]
    elif file_type_enum == IATIFileTypes.ORGANIZATION_BUDGET_FILE:
        return [
            "organisation_identifier",
            "budget_kind",
            "budget_status",
            "period_start",
            "period_end",
            "value",
            "currency",
        ]
    elif file_type_enum == IATIFileTypes.ORGANIZATION_EXPENDITURE_FILE:
        return [
            "organisation_identifier",
            "period_start",
            "period_end",
            "value",
            "currency",
            "value_date",
        ]
    elif file_type_enum == IATIFileTypes.ORGANIZATION_DOCUMENT_FILE:
        return [
            "organisation_identifier",
            "url",
            "format",
            "title",
            "category_code",
            "language",
            "document_date",
        ]
    else:
        raise toolkit.ValidationError(
            {"file_type": f"Unsupported validation for {file_type_enum.name}"}
        )


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


def extract_file_type(res):
    """
    Get iati_file_type from resource attributes or extras.
    """
    file_type = res.get("iati_file_type")
    if file_type:
        return file_type

    for extra in res.get("extras", []):
        if extra.get("key") == "iati_file_type":
            return extra.get("value")
    return None


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


def get_namespace(res):
    """
    Resolve namespace for a resource (attr, extras, or default).
    """
    ns = res.get("iati_namespace")
    if not ns:
        ns = get_namespace_extra(res.get("extras", []))
    if not ns:
        ns = DEFAULT_NAMESPACE
    return ns


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


def get_namespace_extra(extras):
    """
    Given a list of extras (dicts with 'key' and 'value'), return the value
    of the 'iati_namespace' extra, or None if not found.
    """
    for extra in extras:
        if extra.get("key") == "iati_namespace":
            print(f"Found namespace extra: {extra.get('value')}")
            log.debug(f"Found namespace extra: {extra.get('value')}")
            return extra.get("value")
    return None
