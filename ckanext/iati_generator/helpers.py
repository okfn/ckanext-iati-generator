import logging
from pathlib import Path

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
    Returns a list of distinct IATI namespaces from the IATIFile records.
    """
    session = model.Session
    rows = (
        session.query(IATIFile.namespace)
        .distinct()
        .order_by(IATIFile.namespace)
        .all()
    )
    return [r[0] for r in rows if r[0]]


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


def check_mandatory_components(namespace, file_category='organization'):
    """
    Check if all mandatory components are defined for a namespace.

    Args:
        namespace: The IATI namespace to check
        file_category: 'organization' or 'activities'

    Returns:
        dict: {
            'complete': bool,
            'missing': list of missing file types,
            'present': list of present file types
        }
    """

    session = model.Session

    # Define mandatory components for each category
    if file_category == 'organization':
        mandatory_types = [
            IATIFileTypes.ORGANIZATION_MAIN_FILE.value,
        ]
    elif file_category == 'activities':
        mandatory_types = [
            IATIFileTypes.ACTIVITY_MAIN_FILE.value,
        ]
    else:
        raise ValueError(f"Unknown file_category: {file_category}")

    # Query existing files for this namespace
    existing_files = (
        session.query(IATIFile.file_type)
        .filter(IATIFile.namespace == namespace)
        .filter(IATIFile.file_type.in_(mandatory_types))
        .all()
    )

    existing_types = [f[0] for f in existing_files]
    missing_types = [ft for ft in mandatory_types if ft not in existing_types]

    return {
        'complete': len(missing_types) == 0,
        'missing': [IATIFileTypes(ft).name for ft in missing_types],
        'present': [IATIFileTypes(ft).name for ft in existing_types]
    }


def namespace_ready_for_generation(namespace):
    """
    Check if a namespace is ready for IATI generation.
    Returns dict with status for organization and activities.
    """
    org_status = check_mandatory_components(namespace, 'organization')
    act_status = check_mandatory_components(namespace, 'activities')

    return {
        'organization': org_status,
        'activities': act_status,
        'ready': org_status['complete'] or act_status['complete']
    }
