import logging
import csv

from ckan.plugins import toolkit
from ckan import model

from ckanext.iati_generator.csv import row_to_iati_activity
from ckanext.iati_generator.utils import generate_final_iati_xml, get_resource_file_path
from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE, IATIFile
from ckanext.iati_generator.models.enums import IATIFileTypes


log = logging.getLogger(__name__)


def get_validated_csv_data(context, resource_id):
    logs = []
    resource_name = None
    activities = []
    errored_rows = 0

    # Validate existence of the resource and get its name
    resource = toolkit.get_action("resource_show")(context, {"id": resource_id})
    resource_name = resource.get("name", "resource")

    # Validate file type and get path
    path = get_resource_file_path(context, resource_id)
    logs.append(f"Reading CSV at: {path}")

    # Read CSV and validate headers
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        log.info(f"CSV headers: {fieldnames}")
        logs.append(f"CSV headers: {fieldnames}")

        required_fields = ["iati_identifier", "reporting_org_ref", "reporting_org_type", "reporting_org_name", "title"]
        missing = [field for field in required_fields if field not in fieldnames]

        if missing:
            raise ValueError(f"Missing required columns in CSV header: {', '.join(missing)}")

        ROWS_LIMIT = int(toolkit.config.get("ckanext.iati_generator.rows_limit", 50000))
        MAX_ALLOWED_FAILURES = int(toolkit.config.get("ckanext.iati_generator.max_allowed_failures", 10))

        for i, row in enumerate(reader):
            if i >= ROWS_LIMIT:
                logs.append(f"Row limit reached ({ROWS_LIMIT}); stopping")
                break
            try:
                activity = row_to_iati_activity(row)
                activities.append(activity)
            except Exception as e:
                msg = f"Row {i+1}: error ({e}); skipping."
                logs.append(msg)
                log.error(msg)
                errored_rows += 1
                if errored_rows > MAX_ALLOWED_FAILURES:
                    logs.append(f"Max allowed failures reached ({MAX_ALLOWED_FAILURES}); stopping")
                    break

    return activities, logs, resource_name


@toolkit.side_effect_free
def iati_csv_to_activities(context, data_dict):
    """
    Read & validate a CKAN resource CSV and return IATI activities in memory.
    Useful hook point for external extensions to preprocess/transform CSV rows
    before turning them into IATI activities.
    """
    resource_id = data_dict.get("resource_id")
    if not resource_id:
        raise toolkit.ValidationError({"resource_id": "Missing resource_id"})

    try:
        activities, logs, resource_name = get_validated_csv_data(context, resource_id)
    except Exception as e:
        msg = f"Error validating CSV data: {e}"
        log.error(msg)
        return {"activities": [], "logs": [msg], "resource_name": None, "error": msg}

    return {
        "activities": activities,
        "logs": logs,
        "resource_name": resource_name,
        "error": None,
    }


@toolkit.side_effect_free
def iati_activities_to_xml(context, data_dict):
    """
    Turn a list of in-memory IATI activities into a final XML string.
    External extensions can override this to inject extra steps
    (e.g., enrichment, validation, post-processing).
    """
    activities = data_dict.get("activities") or []
    logs = list(data_dict.get("logs") or [])
    if not activities:
        error = "No activities provided"
        logs.append(error)
        return {"xml_string": None, "logs": logs, "error": error}

    try:
        xml_string = generate_final_iati_xml(activities)
    except Exception as e:
        msg = f"Error during IATI generation: {e}"
        log.error(msg)
        logs.append(msg)
        return {"xml_string": None, "logs": logs, "error": msg}

    logs.append("IATI XML generated successfully from activities")
    return {"xml_string": xml_string, "logs": logs, "error": None}


def generate_iati_xml(context, data_dict):
    """
    Orchestrates the chain:
      1) iati_csv_to_activities
      2) iati_activities_to_xml
    External extensions can override any of the two steps.

    data_dict must include:
      - resource_id: the resource to read from

    Returns:
      - xml_string, logs, resource_name, error
    """
    logs = []
    resource_id = data_dict.get("resource_id")
    logs.append(f"Start generating IATI XML file for resource: {resource_id}")

    # ---- Step 1: CSV -> activities (try registry, fallback local) ----
    try:
        step1_action = toolkit.get_action("iati_csv_to_activities")
    except KeyError:
        # Fallback to local implementation if the action is not registered in the registry (e.g., in tests)
        step1_action = iati_csv_to_activities

    step1 = step1_action(context, {"resource_id": resource_id})
    logs.extend(step1.get("logs", []))
    if step1.get("error"):
        return {"xml_string": None, "logs": logs, "resource_name": None, "error": step1["error"]}

    if not step1.get("activities"):
        error = "No valid activities found in the CSV file"
        logs.append(error)
        return {"xml_string": None, "logs": logs, "resource_name": step1.get("resource_name"), "error": error}

    # ---- Step 2: activities -> XML (try registry, fallback local) ----
    try:
        step2_action = toolkit.get_action("iati_activities_to_xml")
    except KeyError:
        # Fallback to local implementation if the action is not registered in the registry
        step2_action = iati_activities_to_xml

    step2 = step2_action(context, {
        "activities": step1["activities"],
        "logs": logs,
        "resource_name": step1.get("resource_name")
    })

    logs = step2.get("logs", logs)
    if step2.get("error"):
        return {"xml_string": None, "logs": logs, "resource_name": None, "error": step2["error"]}

    logs.append(f"IATI XML generated successfully for file: {step1.get('resource_name')}")
    return {
        "xml_string": step2["xml_string"],
        "logs": logs,
        "resource_name": step1.get("resource_name"),
        "error": None
    }


@toolkit.side_effect_free
def list_datasets_with_iati(context, data_dict=None):
    """
    Returns all datasets that have a generated IATI resource,
    identified by the extra 'iati_base_resource_id'.
    Supports optional pagination via 'start' and 'rows'.
    """
    # Ensure data_dict is a dictionary
    data_dict = data_dict or {}

    # Extract parameters with default values
    start = data_dict.get("start", 0)
    rows = data_dict.get("rows", 100)

    search_result = toolkit.get_action("package_search")(context, {
        "q": "extras_iati_base_resource_id:[* TO *]",
        "start": start,
        "rows": rows,
        "sort": "metadata_modified desc"
    })

    return search_result["results"]


def iati_file_create(context, data_dict):
    """
    Create an IATIFile record linked to a CKAN resource.
    Only organization admins can create files for their resources.
    """
    toolkit.check_access('iati_file_create', context, data_dict)

    if 'resource_id' not in data_dict or not data_dict['resource_id']:
        raise toolkit.ValidationError({'resource_id': 'Missing required field resource_id'})
    if 'file_type' not in data_dict:
        raise toolkit.ValidationError({'file_type': 'Missing required field file_type'})
    try:
        # acepta int o nombre del enum
        ft = data_dict['file_type']
        if isinstance(ft, str):
            data_dict['file_type'] = IATIFileTypes[ft].value
        else:
            _ = IATIFileTypes(ft)  # valida que exista
    except Exception:
        raise toolkit.ValidationError({'file_type': 'Invalid IATIFileTypes value'})

    file = IATIFile(
        namespace=data_dict.get('namespace', DEFAULT_NAMESPACE),
        file_type=data_dict['file_type'],
        resource_id=data_dict['resource_id'],
    )
    file.save()
    return toolkit.get_action('iati_file_show')(context, {'id': file.id})


def iati_file_update(context, data_dict):
    """
    Update an existing IATIFile record.
    """
    toolkit.check_access('iati_file_update', context, data_dict)

    session = model.Session
    file = session.query(IATIFile).get(data_dict['id'])
    if not file:
        raise toolkit.ObjectNotFound(f"IATIFile {data_dict['id']} not found")

    for key in ['namespace', 'file_type', 'is_valid', 'last_error']:
        if key in data_dict:
            setattr(file, key, data_dict[key])

    file.save()
    return toolkit.get_action('iati_file_show')(context, {'id': file.id})


def iati_file_delete(context, data_dict):
    """
    Delete an existing IATIFile.
    """
    toolkit.check_access('iati_file_delete', context, data_dict)

    session = model.Session
    file = session.query(IATIFile).get(data_dict['id'])
    if not file:
        raise toolkit.ObjectNotFound(f"IATIFile {data_dict['id']} not found")

    session.delete(file)
    session.commit()
    return {'success': True}


def iati_file_show(context, data_dict):
    """
    Get a single IATIFile by ID.
    """
    toolkit.check_access('iati_file_show', context, data_dict)

    session = model.Session
    file = session.query(IATIFile).get(data_dict['id'])
    if not file:
        raise toolkit.ObjectNotFound(f"IATIFile {data_dict['id']} not found")

    return {
        'id': file.id,
        'namespace': file.namespace,
        'file_type': IATIFileTypes(file.file_type).name,
        'resource_id': file.resource_id,
        'is_valid': file.is_valid,
        'last_error': file.last_error,
        'metadata_created': file.metadata_created.isoformat(),
        'metadata_updated': file.metadata_updated.isoformat() if file.metadata_updated else None,
    }
