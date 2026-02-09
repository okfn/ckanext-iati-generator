import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import re
from ckan.plugins import toolkit
from ckan import model
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE, IATIFile
from ckanext.iati_generator.iati.resource import save_resource_data


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


def iati_files_by_resource(namespace=None):
    """
    Returns an index {resource_id: IATIFile} to allow simple
    validation status queries.

    If namespace is provided, returns only files for that namespace.
    """
    session = model.Session
    q = session.query(IATIFile)
    if namespace:
        q = q.filter(IATIFile.namespace == namespace)
    files = q.all()
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

    int_filetype = normalize_file_type_strict(file_type)
    label = IATIFileTypes(int_filetype).name
    return int_filetype, label


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


def normalize_file_type_strict(value):
    """
    Normalizes file_type to integer.
    Accepts:
        - int
        - numeric string ("100")
        - enum name ("ORGANIZATION_MAIN_FILE")

    Returns:
        int file_type

    Raises ValidationError if not valid.
    """
    try:
        ft = value
        # string?
        if isinstance(ft, str):
            # is it a number?
            if ft.isdigit():
                ft = int(ft)
                IATIFileTypes(ft)  # validate it exists
            else:
                # it's an enum name
                ft = IATIFileTypes[ft].value
        else:
            # must be int (or castable to int)
            IATIFileTypes(ft)  # validate it exists

        return int(ft)

    except Exception:
        raise toolkit.ValidationError(
            {"file_type": "Invalid IATIFileTypes value"}
        )


def iati_namespaces():
    """
    Returns a list of distinct IATI namespaces.

    We search for all the datasets with iati_namespace and return a unique list (in case
    there are multiple datasets with the same namespace)

    TODO: Should we allow multiple datasets with the same namespace?
    """
    ctx = {'user': toolkit.g.user}
    result = toolkit.get_action("package_search")(ctx, {"fq": "iati_namespace:[* TO *]"})
    datasets = result.get("results", [])
    namespaces = [dataset["iati_namespace"] for dataset in datasets]
    return list(set(namespaces))


def process_org_file_type(
    context,
    output_folder: Path,
    filename: str,
    file_type: IATIFileTypes,
    namespace: str,
    required: bool = True,
    max_files: int | None = 1,
) -> int:
    """
    Fetch all IATIFile records of a given organization file_type+namespace,
    download their CSV resource to `output_folder / filename` and track processing.

    Returns:
        int: number of successfully processed files.
    """
    log.info(f"Processing organization file type: {file_type.name} -> {filename}")

    session = model.Session
    query = (
        session.query(IATIFile)
        .filter(IATIFile.file_type == file_type.value)
        .filter(IATIFile.namespace == namespace)
    )

    org_files = query.all()

    # Validate requirements
    if len(org_files) == 0:
        if required:
            raise Exception(f"No organization IATI files of type {file_type.name} found.")
        log.info(f"No files found for optional type {file_type.name}")
        return 0

    if max_files and len(org_files) > max_files:
        raise Exception(
            f"Expected no more than {max_files} organization IATI file(s) of type {file_type.name}, "
            f"found {len(org_files)}."
        )

    processed_count = 0

    for iati_file in org_files:
        log.info(f"Processing IATI file: {iati_file}")
        destination_path = output_folder / filename

        try:
            final_path = save_resource_data(iati_file.resource_id, str(destination_path))

        except Exception as e:
            log.error(f"Error processing file {iati_file.resource_id}: {e}")
            iati_file.track_processing(success=False, error_message=str(e))
            if required:
                raise

        if not final_path:
            log.error(f"Failed to fetch data for resource ID: {iati_file.resource_id}")
            error_message = "Failed to save resource data"
            iati_file.track_processing(success=False, error_message=error_message)
            continue

        iati_file.track_processing(success=True)
        processed_count += 1
        log.info(f"Saved organization CSV data to {final_path}")

    return processed_count


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


def upsert_final_iati_file(resource_id, namespace, file_type, success=True, error_message=None):
    """
    Ensure there is an IATIFile row for the FINAL xml resource and track processing result.
    This is required so the public /iati/<ns>/*.xml endpoints can resolve the latest valid file.
    """
    session = model.Session

    iati_file = session.query(IATIFile).filter(IATIFile.resource_id == resource_id).first()
    if not iati_file:
        iati_file = IATIFile(
            namespace=namespace,
            file_type=file_type,
            resource_id=resource_id,
        )
        session.add(iati_file)
        session.commit()

    iati_file.namespace = namespace
    iati_file.file_type = file_type

    iati_file.track_processing(success=success, error_message=error_message)

    return iati_file


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


# XML element → CSV file mapping
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

# Regex patterns for XSD errors
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
    if normalized.startswith("transaction"):
        return "transactions.csv"
    if normalized.startswith("activity-date"):
        return "activity_date.csv"
    if normalized.startswith("contact"):
        return "contact_info.csv"
    return None


def _parse_schema_error_line(raw: str) -> Dict[str, Any]:
    # Strip common prefixes added by converters
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


def _make_suggestion_for_ordering(element: str, expected: str) -> str:
    """
    Suggestion based ONLY on what the XSD error says (expected elements),
    without hardcoding ordering rules beyond the schema-provided expectation.
    """
    expected_list = _to_pretty_element_list(expected)
    expected_first = expected_list[0] if expected_list else None

    # Try to map expected element to CSV (more useful than mapping the found element)
    expected_csv = _guess_csv_from_element(expected_first) if expected_first else None

    if expected_first:
        if expected_csv:
            return (
                f"El esquema esperaba <{expected_first}> antes de <{element}>. "
                f"Revisá que {expected_csv} exista y tenga datos válidos para estas actividades."
            )
        return (
            f"El esquema esperaba <{expected_first}> antes de <{element}>. "
            "Revisá los CSV que generan esos elementos."
        )

    # Fallback if we couldn't parse expected
    return (
        "El orden/estructura XML no coincide con el esquema. "
        f"Revisá los CSV relacionados con '{element}' y los elementos esperados: ({expected})."
    )


def _to_pretty_element_list(expected: str) -> List[str]:
    return [p.strip() for p in expected.split(",") if p.strip()]


def _flatten_error_dict(errors: Any) -> List[str]:
    """Flatten nested error dict/list into list of strings."""
    raw_lines = []

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
    """Process element ordering errors. Returns True if matched."""
    m = _RE_ELEMENT_NOT_EXPECTED.search(msg_clean)
    if m:
        element = m.group("element")
        expected = m.group("expected")
        expected_list = _to_pretty_element_list(expected)
        item.update({
            "category": "schema",
            "title": "Elemento fuera de orden",
            "element": element,
            "expected": expected_list,
            "csv_file": _guess_csv_from_element(element),
            "suggestion": _make_suggestion_for_ordering(element, expected),
        })
        return True
    return False


def _process_missing_children_error(msg_clean: str, item: Dict[str, Any]) -> bool:
    """Process missing children errors. Returns True if matched."""
    m = _RE_ELEMENT_MISSING.search(msg_clean)
    if m:
        element = m.group("element")
        expected = m.group("expected")
        expected_list = _to_pretty_element_list(expected)
        csv_guess = _guess_csv_from_element(element) or _guess_csv_from_element(expected_list[0] if expected_list else None)
        item.update({
            "category": "schema",
            "title": "Faltan elementos requeridos",
            "element": element,
            "expected": expected_list,
            "csv_file": csv_guess,
            "suggestion": (
                f"Faltan elementos hijos obligatorios dentro de '{element}'. "
                f"Verificá que los CSV que generan {expected_list} existan y tengan filas válidas."
            ),
        })
        return True
    return False


def _process_invalid_value_error(msg_clean: str, item: Dict[str, Any]) -> bool:
    """Process invalid value (pattern) errors. Returns True if matched."""
    m = _RE_INVALID_VALUE.search(msg_clean)
    if m:
        element = m.group("element")
        value = m.group("value")
        item.update({
            "category": "value",
            "title": "Valor inválido",
            "element": element,
            "value": value,
            "csv_file": _guess_csv_from_element(element),
            "suggestion": f"El valor '{value}' no cumple el formato esperado para '{element}'.",
        })
        return True
    return False


def _process_enum_error(msg_clean: str, item: Dict[str, Any]) -> bool:
    """Process enumeration errors. Returns True if matched."""
    m = _RE_ENUM.search(msg_clean)
    if m:
        element = m.group("element")
        value = m.group("value")
        item.update({
            "category": "value",
            "title": "Código no permitido",
            "element": element,
            "value": value,
            "csv_file": _guess_csv_from_element(element),
            "suggestion": f"El valor '{value}' no está permitido para '{element}'. Revisá los códigos válidos.",
        })
        return True
    return False


def _process_type_error(msg_clean: str, item: Dict[str, Any]) -> bool:
    """Process invalid type errors. Returns True if matched."""
    m = _RE_SIMPLE_TYPE.search(msg_clean)
    if m:
        element = m.group("element")
        value = m.group("value")
        item.update({
            "category": "value",
            "title": "Tipo de dato inválido",
            "element": element,
            "value": value,
            "csv_file": _guess_csv_from_element(element),
            "suggestion": f"El valor '{value}' no es del tipo correcto para '{element}'.",
        })
        return True
    return False


def _process_fallback_error(msg_clean: str, item: Dict[str, Any]) -> None:
    """Extract element from error message as fallback."""
    m_el = re.search(r"Element\s+'([^']+)'", msg_clean)
    if m_el:
        element = m_el.group(1)
        item["element"] = element
        item["csv_file"] = _guess_csv_from_element(element)
        item["category"] = "schema"


def _normalize_single_error(raw: str, parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a single error line into structured format."""
    msg = parsed.get("msg", raw)
    msg_clean = msg.strip()

    item: Dict[str, Any] = {
        "severity": "error",
        "category": "unknown",
        "title": "Error de validación",
        "details": msg_clean,
        "suggestion": "Revisá los archivos CSV requeridos y su formato.",
        "raw": raw,
    }

    if "line" in parsed and "col" in parsed:
        item["location"] = {"line": parsed["line"], "col": parsed["col"]}

    # Try to match specific error patterns
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

    # Fallback: try to extract element
    _process_fallback_error(msg_clean, item)
    return item


def _deduplicate_errors(normalized: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate error items based on key fields."""
    seen = set()
    deduped = []
    for it in normalized:
        key = (it.get("title"), it.get("details"), it.get("element"), str(it.get("location")))
        if key not in seen:
            seen.add(key)
            deduped.append(it)
    return deduped


def _generate_summary(package_id: Optional[str]) -> Optional[str]:
    """Generate summary message with pending files count."""
    if not package_id:
        return None
    
    pending = get_pending_mandatory_files(package_id)
    missing_count = len(pending.get("organization", [])) + len(pending.get("activity", []))
    if missing_count > 0:
        return f"No se pudo generar el XML porque faltan o están mal formados {missing_count} archivo(s) CSV obligatorios."
    return None


def normalize_iati_errors(error_dict: Any, package_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Normalize IATI XSD errors into user-friendly structure.
    Returns:
        {
            "summary": str | None,
            "items": [
                {
                    "severity": "error",
                    "category": "schema" | "value" | "unknown",
                    "title": "...",
                    "element": "contact-info",
                    "csv_file": "contact_info.csv",
                    "location": {"line": 19, "col": 0},
                    "details": "...",
                    "suggestion": "...",
                    "raw": "..."
                }
            ],
            "raw": [original error strings]
        }
    """
    raw_lines = _flatten_error_dict(error_dict)
    log.debug(f"normalize_iati_errors: Processing {len(raw_lines)} raw error lines")
    if raw_lines:
        log.debug(f"Sample error: {raw_lines[0][:150]}")

    normalized = []
    for raw in raw_lines:
        parsed = _parse_schema_error_line(raw)
        item = _normalize_single_error(raw, parsed)
        normalized.append(item)

    deduped = _deduplicate_errors(normalized)
    summary = _generate_summary(package_id)

    return {
        "summary": summary,
        "items": deduped,
        "raw": raw_lines,
    }
