import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import re
from ckan.plugins import toolkit
from ckan import model
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE

from okfn_iati import IatiMultiCsvConverter
from okfn_iati.organisation_xml_generator import IatiOrganisationMultiCsvConverter


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


def normalize_namespace(ns):
    """
    Normalize a namespace string by applying consistent formatting rules.

    If the namespace is None or empty, returns the default namespace.
    Otherwise, strips whitespace and replaces internal whitespace sequences with hyphens.

    Args:
        ns (str or None): The namespace string to normalize.

    Returns:
        str: A normalized namespace string with whitespace stripped and internal
             spaces replaced with hyphens, or DEFAULT_NAMESPACE if input is None/empty.

    Examples:
        >>> normalize_namespace("my  namespace")
        'my-namespace'
        >>> normalize_namespace("  test  ")
        'test'
        >>> normalize_namespace(None)
        DEFAULT_NAMESPACE
        >>> normalize_namespace("")
        DEFAULT_NAMESPACE
    """
    if ns is None:
        return DEFAULT_NAMESPACE
    ns = str(ns).strip()
    if not ns:
        return DEFAULT_NAMESPACE
    # opcional: compactar espacios internos
    ns = re.sub(r"\s+", "-", ns)
    return ns


def get_iati_files(package_id):
    """Get a list of the existing IATIFileTypes for a specific package."""
    ctx = {"user": toolkit.g.user}

    dataset = toolkit.get_action("package_show")(ctx, {"id": package_id})

    iati_types = [res.get("iati_file_type", "") for res in dataset.get("resources", [])]
    iati_enums = [IATIFileTypes(int(key)) for key in iati_types if key]

    return set(iati_enums)


def mandatory_file_types():
    """Return a list of mandatory file types.

    For now, mandatory files are the ones that okfn_iati MultiCSVConvert needs.
    """
    org = [
        IATIFileTypes.ORGANIZATION_MAIN_FILE,
    ]

    # https://github.com/okfn/okfn_iati/blob/999c24156cd741e3ea2c0c1a2da434ec7bd8feb9/src/okfn_iati/multi_csv_converter.py#L56
    act = [
        IATIFileTypes.ACTIVITY_MAIN_FILE,
        IATIFileTypes.ACTIVITY_CONTACT_INFO_FILE,
        IATIFileTypes.ACTIVITY_DOCUMENTS_FILE,
        IATIFileTypes.ACTIVITY_INDICATORS_FILE,
        IATIFileTypes.ACTIVITY_INDICATOR_PERIODS_FILE,
        IATIFileTypes.ACTIVITY_RESULTS_FILE,
        IATIFileTypes.ACTIVITY_SECTORS_FILE,
        IATIFileTypes.ACTIVITY_TRANSACTIONS_FILE,
    ]
    return set(org), set(act)


def get_pending_mandatory_files(package_id):
    """Returns pending mandatory files for the namespace."""
    mandatory_org, mandatory_act = mandatory_file_types()

    present_files = get_iati_files(package_id)
    pending_org = mandatory_org - present_files
    pending_act = mandatory_act - present_files

    result = {
        "organization": sorted(pending_org, key=lambda x: x.value),
        "activity": sorted(pending_act, key=lambda x: x.value),
    }

    return result


def has_final_iati_resource(pkg_dict, final_type_name: str) -> bool:
    """
    Check if the package has a resource of the specified final IATI type.
    Used to show or hide public download links for the final XML in the dataset's IATI files view.
    """
    final_value = int(getattr(IATIFileTypes, final_type_name).value)

    for res in (pkg_dict or {}).get("resources", []) or []:
        ft = res.get("iati_file_type")

        # sometimes it may come from extras list
        if not ft:
            for extra in res.get("extras", []) or []:
                if extra.get("key") == "iati_file_type":
                    ft = extra.get("value")
                    break

        if ft is None:
            continue

        # normalize to int if possible
        try:
            if int(ft) == final_value:
                return True
        except (ValueError, TypeError):
            continue

    return False


# XML element → CSV file mapping (only to improve suggestions in XSD errors)
# NOTE: this does NOT define "required files". The source of truth for required files is okfn_iati.required_csv_files().
XML_TO_CSV_MAP: Dict[str, str] = {
    # Activities
    "iati-activity": "activities.csv",
    "activity-date": "activity_date.csv",
    "contact-info": "contact_info.csv",
    "transaction": "transactions.csv",
    "sector": "sectors.csv",
    "location": "locations.csv",
    "document-link": "documents.csv",
    "result": "results.csv",
    "indicator": "indicators.csv",
    "period": "indicator_periods.csv",
    "condition": "conditions.csv",
    "description": "descriptions.csv",
    "country-budget-items": "country_budget_items.csv",
    "participating-org": "participating_orgs.csv",
    "budget": "budgets.csv",
    "transaction-sector": "transaction_sectors.csv",
    # Organisations
    "iati-organisation": "organisations.csv",
    "organisation": "organisations.csv",
    "organization": "organisations.csv",
    "name": "names.csv",
    "expenditure": "expenditures.csv",
}


def required_activity_csv_files() -> List[str]:
    """
    Source of truth: okfn_iati.IatiMultiCsvConverter.required_csv_files()
    Returns the canonical names (e.g., activities.csv) expected in the temporary folder.
    """
    return list(IatiMultiCsvConverter.required_csv_files())


def required_organisation_csv_files() -> List[str]:
    """
    Source of truth: okfn_iati.IatiOrganisationMultiCsvConverter.required_csv_files()
    """
    return list(IatiOrganisationMultiCsvConverter.required_csv_files())


def validate_required_csv_folder(
    folder: Path,
    required_files: List[str],
) -> Dict[str, Any]:
    """
    Pre-check of required CSV files BEFORE running the converter.

    - missing: the file does not exist in the folder
    - invalid: empty / unreadable / no header (and optionally: no data rows)

    Returns {} if everything is OK.
    If there are issues, returns a dict ALREADY normalized with the same structure as normalize_iati_errors().
    """
    missing: List[str] = []
    invalid: List[str] = []

    for fname in required_files:
        p = folder / fname
        if not p.exists():
            missing.append(fname)
            continue

    if not missing and not invalid:
        return {}

    items: List[Dict[str, Any]] = []

    for f in missing:
        items.append({
            "severity": "error",
            "category": "missing-file",
            "title": toolkit._("Required CSV file missing"),
            "csv_file": f,
            "details": toolkit._(
                "%(csv_file)s was not found in the build folder."
            ) % {
                "csv_file": f,
            },
            "suggestion": toolkit._(
                "Upload %(csv_file)s as a dataset resource (with the correct IATI file type) and try again."
            ) % {
                "csv_file": f,
            },
            "raw": f"missing:{f}",
        })

    return {
        "summary": toolkit._(
            "The XML could not be generated because required CSV files are missing or malformed."
        ),
        "items": items,
        "raw": [it["raw"] for it in items],
    }


_RE_SCHEMA_POS = re.compile(
    r"<string>:(?P<line>\d+):(?P<col>\d+):(?P<level>[A-Z]+):(?P<domain>[^:]+):(?P<code>[^:]+):\s*(?P<msg>.*)$"
)
_RE_ELEMENT_NOT_EXPECTED = re.compile(
    r"Element\s+'(?P<element>[^']+)':\s+This element is not expected\.\s+Expected is\s+\(\s*(?P<expected>[^)]+)\s*\)\.",
    re.IGNORECASE,
)
_RE_ELEMENT_MISSING = re.compile(
    r"Element\s+'(?P<element>[^']+)':\s+Missing child element\(s\)\.\s+Expected is\s+\(\s*(?P<expected>[^)]+)\s*\)\.",
    re.IGNORECASE,
)
_RE_INVALID_VALUE = re.compile(
    r"Element\s+'(?P<element>[^']+)':\s+\[facet\s+'(?P<facet>[^']+)'\]\s+The value\s+'(?P<value>[^']*)'\s+is\s+not\s+accepted",
    re.IGNORECASE,
)
_RE_ENUM = re.compile(
    r"Element\s+'(?P<element>[^']+)':\s+\[facet\s+'enumeration'\]\s+The value\s+'(?P<value>[^']*)'\s+is\s+not\s+an\s+element",
    re.IGNORECASE,
)
_RE_SIMPLE_TYPE = re.compile(
    r"Element\s+'(?P<element>[^']+)':\s+'(?P<value>[^']*)'\s+is\s+not\s+a\s+valid\s+value\s+of\s+the\s+atomic\s+type",
    re.IGNORECASE,
)


def _guess_csv_from_element(element: Optional[str]) -> Optional[str]:
    if not element:
        return None

    if element in XML_TO_CSV_MAP:
        return XML_TO_CSV_MAP[element]

    normalized = element.split(":")[-1]
    if normalized in XML_TO_CSV_MAP:
        return XML_TO_CSV_MAP[normalized]

    # heurísticas mínimas
    if normalized.startswith("transaction"):
        return "transactions.csv"
    if normalized.startswith("activity-date"):
        return "activity_date.csv"
    if normalized.startswith("contact"):
        return "contact_info.csv"

    return None


def _parse_schema_error_line(raw: str) -> Dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("Schema: "):
        cleaned = cleaned[8:]  # Remove "Schema: " prefix

    m = _RE_SCHEMA_POS.match(cleaned)
    if not m:
        return {"raw": raw}
    d = m.groupdict()
    d["line"] = int(d["line"])
    d["col"] = int(d["col"])
    return d


def _to_pretty_element_list(expected: str) -> List[str]:
    return [p.strip() for p in expected.split(",") if p.strip()]


def _make_suggestion_for_ordering(element: str, expected: str) -> str:
    expected_list = _to_pretty_element_list(expected)
    expected_first = expected_list[0] if expected_list else None
    expected_csv = _guess_csv_from_element(expected_first) if expected_first else None

    if expected_first:
        if expected_csv:
            return toolkit._(
                "The schema expected <%(expected_first)s> before <%(element)s>. "
                "Check that %(expected_csv)s exists and contains valid data for these activities."
            ) % {
                "expected_first": expected_first,
                "element": element,
                "expected_csv": expected_csv,
            }

        return toolkit._(
            "The schema expected <%(expected_first)s> before <%(element)s>. "
            "Check the CSV files that generate those elements."
        ) % {
            "expected_first": expected_first,
            "element": element,
        }

    return toolkit._(
        "The order/structure of the XML does not match the schema. "
        "Check the related CSV files for '%(element)s' and the expected elements: (%(expected)s)."
    ) % {
        "element": element,
        "expected": ", ".join(expected_list) if expected_list else expected,
    }


def _flatten_error_dict(errors: Any) -> List[str]:
    raw_lines: List[str] = []

    def _walk(obj):
        if obj is None:
            return
        if isinstance(obj, str):
            raw_lines.append(obj)
        elif isinstance(obj, list):
            for it in obj:
                _walk(it)
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        else:
            raw_lines.append(str(obj))

    _walk(errors)
    return raw_lines


def _process_element_ordering_error(msg_clean: str, item: Dict[str, Any]) -> bool:
    m = _RE_ELEMENT_NOT_EXPECTED.search(msg_clean)
    if not m:
        return False

    element = m.group("element")
    expected = m.group("expected")
    expected_list = _to_pretty_element_list(expected)

    # preferir CSV del expected (más útil que el element encontrado)
    csv_expected = _guess_csv_from_element(expected_list[0] if expected_list else None)

    item.update({
        "category": "schema",
        "title": toolkit._("Element out of order"),
        "element": element,
        "expected": expected_list,
        "csv_file": csv_expected or _guess_csv_from_element(element),
        "suggestion": _make_suggestion_for_ordering(element, expected),
    })
    return True


def _process_missing_children_error(msg_clean: str, item: Dict[str, Any]) -> bool:
    m = _RE_ELEMENT_MISSING.search(msg_clean)
    if not m:
        return False

    element = m.group("element")
    expected = m.group("expected")
    expected_list = _to_pretty_element_list(expected)
    csv_guess = (
        _guess_csv_from_element(element)
        or _guess_csv_from_element(expected_list[0] if expected_list else None)
    )
    pretty_expected = ", ".join(expected_list) if expected_list else expected

    item.update({
        "category": "schema",
        "title": toolkit._("Missing required elements"),
        "element": element,
        "expected": expected_list,
        "csv_file": csv_guess,
        "suggestion": toolkit._(
            "Missing required child elements within '%(element)s'. "
            "Check that the CSV files generating (%(expected)s) exist and contain valid rows."
        ) % {
            "element": element,
            "expected": pretty_expected,
        },
    })
    return True


def _process_invalid_value_error(msg_clean: str, item: Dict[str, Any]) -> bool:
    m = _RE_INVALID_VALUE.search(msg_clean)
    if not m:
        return False

    element = m.group("element")
    value = m.group("value")
    item.update({
        "category": "value",
        "title": toolkit._("Invalid value"),
        "element": element,
        "value": value,
        "csv_file": _guess_csv_from_element(element),
        "suggestion": toolkit._(
            "The value '%(value)s' does not match the expected format for '%(element)s'."
        ) % {
            "value": value,
            "element": element,
        },
    })
    return True


def _process_enum_error(msg_clean: str, item: Dict[str, Any]) -> bool:
    m = _RE_ENUM.search(msg_clean)
    if not m:
        return False

    element = m.group("element")
    value = m.group("value")
    item.update({
        "category": "value",
        "title": toolkit._("Invalid code"),
        "element": element,
        "value": value,
        "csv_file": _guess_csv_from_element(element),
        "suggestion": toolkit._(
            "The value '%(value)s' is not allowed for '%(element)s'. Check the valid codes."
        ) % {
            "value": value,
            "element": element,
        },
    })
    return True


def _process_type_error(msg_clean: str, item: Dict[str, Any]) -> bool:
    m = _RE_SIMPLE_TYPE.search(msg_clean)
    if not m:
        return False

    element = m.group("element")
    value = m.group("value")
    item.update({
        "category": "value",
        "title": toolkit._("Invalid data type"),
        "element": element,
        "value": value,
        "csv_file": _guess_csv_from_element(element),
        "suggestion": toolkit._(
            "The value '%(value)s' is not of the correct type for '%(element)s'."
        ) % {
            "value": value,
            "element": element,
        },
    })
    return True


def _process_fallback_error(msg_clean: str, item: Dict[str, Any]) -> None:
    m_el = re.search(r"Element\s+'([^']+)'", msg_clean)
    if m_el:
        element = m_el.group(1)
        item["element"] = element
        item["csv_file"] = _guess_csv_from_element(element)
        item["category"] = "schema"


def _normalize_single_error(raw: str, parsed: Dict[str, Any]) -> Dict[str, Any]:
    msg = parsed.get("msg", raw)
    msg_clean = msg.strip()

    item: Dict[str, Any] = {
        "severity": "error",
        "category": "unknown",
        "title": toolkit._("Validation error"),
        "details": msg_clean,
        "suggestion": toolkit._("Check the required CSV files and their format."),
        "raw": raw,
    }

    if "line" in parsed and "col" in parsed:
        item["location"] = {"line": parsed["line"], "col": parsed["col"]}

    if _process_element_ordering_error(msg_clean, item):
        return item
    if _process_missing_children_error(msg_clean, item):
        return item
    if _process_invalid_value_error(msg_clean, item):
        return item
    if _process_enum_error(msg_clean, item):
        return item
    if _process_type_error(msg_clean, item):
        return item

    _process_fallback_error(msg_clean, item)
    return item


def _deduplicate_errors(normalized: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for it in normalized:
        key = (it.get("title"), it.get("details"), it.get("element"), str(it.get("location")))
        if key not in seen:
            seen.add(key)
            deduped.append(it)
    return deduped


def normalize_iati_errors(error_dict: Any, package_id: Optional[str] = None) -> Dict[str, Any]:
    """
    It normalizes converter errors (XSD / latest_errors) into a user-friendly structure.

    It also supports pre-normalized structures (e.g., the output of validate_required_csv_folder()).
    """
    # If already normalized (pre-check), return it as is
    if isinstance(error_dict, dict) and "items" in error_dict and "raw" in error_dict:
        if "summary" not in error_dict or error_dict["summary"] is None:
            error_dict["summary"] = toolkit._(
                "The XML could not be generated due to errors in the source CSV files."
            )
        return error_dict

    raw_lines = _flatten_error_dict(error_dict)

    normalized = []
    for raw in raw_lines:
        parsed = _parse_schema_error_line(raw)
        item = _normalize_single_error(raw, parsed)
        normalized.append(item)

    deduped = _deduplicate_errors(normalized)

    summary = toolkit._(
        "The XML could not be generated due to validation errors in the source CSV files."
    ) if deduped else None

    return {
        "summary": summary,
        "items": deduped,
        "raw": raw_lines,
    }
