import logging
import os
import tempfile
import csv
from datetime import datetime

from ckan.plugins import toolkit

from ckanext.iati_generator.csv import row_to_iati_activity
from ckanext.iati_generator.utils import generate_final_iati_xml, get_resource_file_path


log = logging.getLogger(__name__)


def generate_iati_xml(context, data_dict):
    """ Generate a IATI file froma CSV resource file.
        data_dict should contain:
          - resource_id: the ID of the resource to read from
        Returns a tuple with:
          - file_path: the path to the generated XML file or None if failed
          - logs: a list of logs generated during the process
    """
    # Track all steps in this logs list
    logs = []
    resource_id = data_dict.get("resource_id")
    logs.append(f"Start generting IATI XML file for resource: {resource_id}")

    path = get_resource_file_path(context, resource_id)
    logs.append(f"Reading CSV at: {path}")

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

    # Validate headers
    f = open(path, newline="", encoding="utf-8")
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

    # Limit the number of rows to process to avoid large XML files
    ROWS_LIMIT = int(toolkit.config.get("ckanext.iati_generator.rows_limit", 50000))
    MAX_ALLOWED_FAILURES = int(toolkit.config.get("ckanext.iati_generator.max_allowed_failures", 10))

    # Check if the CSV has the required headers
    activities = []
    errred_rows = 0
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

    f.close()

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

    # Save to a temporary file
    # TODO, investigate about creating/updating a CKAN resource for this or use cases
    # when we use AWS S3 or other storage
    # Save to uniquely named temp file
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    clean_name = resource_name.replace(" ", "_").lower()
    filename = f"{clean_name}_iati_{timestamp}.xml"
    out_path = os.path.join(tempfile.gettempdir(), filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml_string)
    logs.append(f"XML saved to {out_path}")

    return {"file_path": out_path, "logs": logs}
