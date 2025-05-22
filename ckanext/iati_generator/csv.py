"""
Process CSV files to generate IATI XML.
"""
from okfn_iati import (
    Activity, Narrative, OrganizationRef,
)


def row_to_iati_activity(row):
    """
    Convert a CSV row to an IATI Activity object.
    row is a dictionary with keys corresponding to the CSV headers.
    Returns an Activity object.
    """

    required_fields = [
        "iati_identifier",
        "reporting_org_ref",
        "reporting_org_type",
        "reporting_org_name",
        "title"
    ]
    missing_fields = [field for field in required_fields if field not in row]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    activity = Activity(
        iati_identifier=row["iati_identifier"],
        reporting_org=OrganizationRef(
            ref=row["reporting_org_ref"],
            type=row["reporting_org_type"],
            narratives=[Narrative(text=row["reporting_org_name"])]
        ),
        title=[Narrative(text=row["title"])],
    )
    return activity
