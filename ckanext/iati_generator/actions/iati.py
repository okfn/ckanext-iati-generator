import logging
import csv

from ckan.plugins import toolkit

from ckanext.iati_generator.csv import row_to_iati_activity
from ckanext.iati_generator.utils import generate_final_iati_xml, get_resource_file_path


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


def generate_iati_xml(context, data_dict):
    """
    Generate an IATI XML string from a CSV resource file.

    data_dict should contain:
        - resource_id: the ID of the resource to read from

    Returns a dict with:
        - xml_string: the generated IATI XML as a string, or None if failed
        - logs: a list of logs generated during the process
        - resource_name: the name of the resource being processed (or None)
        - error: in case of failure, an error message
    """
    logs = []
    resource_id = data_dict.get("resource_id")
    logs.append(f"Start generating IATI XML file for resource: {resource_id}")

    try:
        activities, csv_logs, resource_name = get_validated_csv_data(context, resource_id)
    except Exception as e:
        msg = f"Error validating CSV data: {e}"
        log.error(msg)
        logs.append(msg)
        return {"xml_string": None, "logs": logs, "resource_name": None, "error": msg}

    logs.extend(csv_logs)
    if not activities:
        error = "No valid activities found in the CSV file"
        logs.append(error)
        return {"xml_string": None, "logs": logs, "resource_name": resource_name, "error": error}

    try:
        xml_string = generate_final_iati_xml(activities)
    except Exception as e:
        msg = f"Error during IATI generation: {e}"
        log.error(msg)
        logs.append(msg)
        return {"xml_string": None, "logs": logs, "resource_name": None, "error": msg}

    logs.append(f"IATI XML generated successfully for file: {resource_name}")
    return {"xml_string": xml_string, "logs": logs, "resource_name": resource_name, "error": None}


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

    result = toolkit.get_action("package_search")(context, {
        "fq": "iati_base_resource_id:*",
        "start": start,
        "rows": rows,
        "sort": "metadata_modified desc"
    })

    for pkg in result["results"]:
        log.debug(f"[IATI Admin] Found dataset: {pkg['name']} - title: {pkg.get('title')}")

    return result["results"]
