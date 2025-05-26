import logging
import csv

from ckan.plugins import toolkit

from ckanext.iati_generator.csv import row_to_iati_activity
from ckanext.iati_generator.utils import generate_final_iati_xml, get_resource_file_path


log = logging.getLogger(__name__)

# Limit the number of rows to process to avoid large XML files
ROWS_LIMIT = int(toolkit.config.get("ckanext.iati_generator.rows_limit", 50000))
MAX_ALLOWED_FAILURES = int(toolkit.config.get("ckanext.iati_generator.max_allowed_failures", 10))


def generate_iati_xml(context, data_dict):
    """ Generate a IATI file from a CSV resource file.
        data_dict should contain:
          - resource_id: the ID of the resource to read from
        Returns a dict with:
          - file_path: the path to the generated XML file or None if failed
          - logs: a list of logs generated during the process
    """
    # Track all steps in this logs list
    logs = []
    resource_id = data_dict.get("resource_id")
    logs.append(f"Start generating IATI XML file for resource: {resource_id}")

    # Get the resource file path and metadata
    path = get_resource_file_path(context, resource_id)
    logs.append(f"Reading CSV at: {path}")

    try:
        resource = toolkit.get_action("resource_show")(context, {"id": resource_id})
        resource_name = resource.get("name", "resource")
    except Exception as e:
        msg = f"Error retrieving resource metadata: {e}"
        log.error(msg)
        logs.append(msg)
        return {"file_path": None, "logs": logs}

    activities = []
    errred_rows = 0

    # Validate headers
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        log.info(f"CSV headers: {fieldnames}")
        logs.append(f"CSV headers: {fieldnames}")

        required_fields = ["iati_identifier", "reporting_org_ref", "reporting_org_type", "reporting_org_name", "title"]
        missing = [field for field in required_fields if field not in fieldnames]

        if missing:
            msg = f"Missing required columns in CSV header: {', '.join(missing)}"
            log.error(msg)
            logs.append(msg)
            return {"file_path": None, "logs": logs}

        # Check if the CSV has the required headers
        for i, row in enumerate(reader):
            if i >= ROWS_LIMIT:
                logs.append(f"Row limit reached ({ROWS_LIMIT}); stopping")
                break

            try:
                act = row_to_iati_activity(row)
                activities.append(act)
            except Exception as e:
                msg = f"Row {i+1}: error ({e}); skipping."
                log.error(msg)
                logs.append(msg)
                errred_rows += 1
                if errred_rows > MAX_ALLOWED_FAILURES:
                    logs.append(f"Max allowed failures reached ({MAX_ALLOWED_FAILURES}); stopping")
                    break

    if not activities:
        logs.append("No valid activities were generated")
        return {"file_path": None, "logs": logs}

    # Generate the IATI XML
    try:
        xml_string = generate_final_iati_xml(activities)
        logs.append("IATI XML generated successfully")
    except Exception as e:
        logs.append(f"Error generating IATI XML: {e}")
        return {"file_path": None, "logs": logs}

    return {"xml_string": xml_string, "logs": logs, "resource_name": resource_name}
