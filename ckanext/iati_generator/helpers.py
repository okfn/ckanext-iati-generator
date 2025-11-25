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


# ===========================================================================
# Required CSV fields per IATI file type
# NOTE: okfn-iati currently does not expose a function for this; if in the future
#       the internal library provides it, we should delegate there to have
#       a single source of truth.
# ===========================================================================


def _required_fields_org_main():
    """Required headers for ORGANIZATION_MAIN_FILE (organisations.csv)."""
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


def _required_fields_org_names():
    """Required headers for ORGANIZATION_NAMES_FILE (names.csv)."""
    return [
        "organisation_identifier",
        "language",
        "name",
    ]


def _required_fields_org_budget():
    """Required headers for ORGANIZATION_BUDGET_FILE (budgets.csv)."""
    return [
        "organisation_identifier",
        "budget_kind",
        "budget_status",
        "period_start",
        "period_end",
        "value",
        "currency",
    ]


def _required_fields_org_expenditure():
    """Required headers for ORGANIZATION_EXPENDITURE_FILE (expenditures.csv)."""
    return [
        "organisation_identifier",
        "period_start",
        "period_end",
        "value",
        "currency",
        "value_date",
    ]


def _required_fields_org_document():
    """Required headers for ORGANIZATION_DOCUMENT_FILE (documents.csv)."""
    return [
        "organisation_identifier",
        "url",
        "format",
        "title",
        "category_code",
        "language",
        "document_date",
    ]


def get_required_fields_by_file_type(file_type_enum):
    """
    Returns a list of required CSV fields based on the IATI file type.

    This is intentionally split into small helpers per file type so that,
    if okfn-iati starts exposing this information, we can replace the
    implementation more easily.
    """
    if file_type_enum == IATIFileTypes.ORGANIZATION_MAIN_FILE:
        return _required_fields_org_main()
    elif file_type_enum == IATIFileTypes.ORGANIZATION_NAMES_FILE:
        return _required_fields_org_names()
    elif file_type_enum == IATIFileTypes.ORGANIZATION_BUDGET_FILE:
        return _required_fields_org_budget()
    elif file_type_enum == IATIFileTypes.ORGANIZATION_EXPENDITURE_FILE:
        return _required_fields_org_expenditure()
    elif file_type_enum == IATIFileTypes.ORGANIZATION_DOCUMENT_FILE:
        return _required_fields_org_document()

    # If we reach here, it's a type we don't support yet
    raise toolkit.ValidationError(
        {"file_type": f"Unsupported validation for {getattr(file_type_enum, 'name', file_type_enum)}"}
    )


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
