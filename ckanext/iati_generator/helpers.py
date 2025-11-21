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


def get_namespace_extra(extras):
    """
    Given a list of extras (dicts with 'key' and 'value'), return the value
    of the 'iati_namespace' extra, or None if not found.
    """
    for extra in extras:
        if extra.get("key") == "iati_namespace":
            return extra.get("value")
    return None
