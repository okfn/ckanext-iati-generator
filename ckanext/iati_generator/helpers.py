import logging
from pathlib import Path

import re
from ckan.plugins import toolkit
from collections import defaultdict
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
    """Get a list of the existing IATIFileTypes for a specific namespace."""
    ctx = {"user": toolkit.g.user}

    dataset = toolkit.get_action("package_show")(ctx, {"id": package_id})

    iati_types = [res.get("iati_file_type", "") for res in dataset.get("resources", [])]
    iati_enums = [IATIFileTypes(int(key)) for key in iati_types]

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
