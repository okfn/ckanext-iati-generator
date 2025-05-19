import logging
import os
import tempfile
import csv
import traceback
import ckan.lib.uploader as uploader
from ckan.plugins import toolkit
from okfn_iati import (
    Activity, Narrative, OrganizationRef,
    IatiActivities, IatiXmlGenerator
)

log = logging.getLogger(__name__)

# Limit the number of rows to process to avoid large XML files
ROWS_LIMIT = int(toolkit.config.get("iati_generator.rows_limit", 50000))


def iati_generate_test_xml(context, data_dict):
    logs = []

    try:
        resource_id = data_dict["resource_id"]
        logs.append(f"resource_id: {resource_id}")

        # 1) Get resource metadata
        resource = toolkit.get_action("resource_show")(context, {"id": resource_id})
        fmt = resource.get("format", "").lower()
        if fmt not in ("csv", "xml"):
            return {"logs": f"Unsupported format '{fmt}'. Only CSV or XML allowed."}
        if resource.get("url_type") != "upload":
            return {"logs": "Resource must be a local upload (url_type='upload')."}

        # 2) Locate the file
        up = uploader.get_resource_uploader(resource)
        path = up.get_path(resource_id)
        logs.append(f"Reading CSV at: {path}")

        # 3) Read rows from the CSV
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        logs.append(f"Loaded {len(rows)} rows (will truncate at {ROWS_LIMIT})")

        # 4) Map to Activity objects
        activities = []
        for i, row in enumerate(rows):
            if i >= ROWS_LIMIT:
                logs.append(f"Row limit reached ({ROWS_LIMIT}); stopping")
                break

            try:
                act = Activity(
                    iati_identifier=row["iati_identifier"],
                    reporting_org=OrganizationRef(
                        ref=row["reporting_org_ref"],
                        type=row["reporting_org_type"],
                        narratives=[Narrative(text=row["reporting_org_name"])]
                    ),
                    title=[Narrative(text=row["title"])],
                    # TODO: add more IATI fields here as needed,
                    # e.g. description=[Narrative(text=row["description"])], etc.
                )
                activities.append(act)
            except KeyError as e:
                log.error(f"Missing required column {e} in row {i+1}; skipping")
            except Exception as e:
                log.error(f"Error mapping row {i+1} to Activity: {e}; skipping")

        if not activities:
            return {"logs": "No valid activities generated; check CSV headers."}

        # 5) Generate the IATI XML
        container = IatiActivities(version="2.03", activities=activities)
        generator = IatiXmlGenerator()
        xml_string = generator.generate_iati_activities_xml(container)
        logs.append("IATI XML generated successfully")

        # 6) Save to a temporary file
        out_path = os.path.join(tempfile.gettempdir(), f"iati_{resource_id}.xml")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(xml_string)
        logs.append(f"XML saved to {out_path}")

        return {
            "file_path": out_path,
            "logs": "\n".join(logs),
        }

    except Exception:
        tb = traceback.format_exc()
        logs.append("Unhandled exception:")
        logs.append(tb)
        return {"logs": "\n".join(logs)}
