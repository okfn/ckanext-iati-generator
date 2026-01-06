# ckanext/iati_generator/iati/activities.py

import logging
from okfn_iati.multi_csv_converter import IatiMultiCsvConverter

from ckan import model
from ckanext.iati_generator.iati.resource import save_resource_data
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE, IATIFile

log = logging.getLogger(__name__)


def process_activity_files(namespace, tmp_folder):
    """
    Download activity CSVs for the namespace, then generate IATI Activities XML.

    Returns:
      dict: { processed_csv: int, converted: bool, xml_path: str }
    """
    act_folder = tmp_folder / f"act-{namespace}"
    act_folder.mkdir(parents=True, exist_ok=True)

    processed_csv = 0

    # Required
    processed_csv += _process_act_file(
        act_folder,
        "activities.csv",
        IATIFileTypes.ACTIVITY_MAIN_FILE,
        required=True,
        max_files=1,
        namespace=namespace,
    )

    # Optional (as per okfn_iati multi csv structure)
    processed_csv += _process_act_file(act_folder, "transactions.csv", IATIFileTypes.ACTIVITY_TRANSACTIONS_FILE,
                                       required=False, max_files=1, namespace=namespace)
    processed_csv += _process_act_file(act_folder, "transaction_sectors.csv", IATIFileTypes.ACTIVITY_TRANSACTION_SECTORS_FILE,
                                       required=False, max_files=1, namespace=namespace)
    processed_csv += _process_act_file(act_folder, "sectors.csv", IATIFileTypes.ACTIVITY_SECTORS_FILE,
                                       required=False, max_files=1, namespace=namespace)
    processed_csv += _process_act_file(act_folder, "budgets.csv", IATIFileTypes.ACTIVITY_BUDGET_FILE,
                                       required=False, max_files=1, namespace=namespace)
    processed_csv += _process_act_file(act_folder, "locations.csv", IATIFileTypes.ACTIVITY_LOCATIONS_FILE,
                                       required=False, max_files=1, namespace=namespace)
    processed_csv += _process_act_file(act_folder, "documents.csv", IATIFileTypes.ACTIVITY_DOCUMENTS_FILE,
                                       required=False, max_files=1, namespace=namespace)
    processed_csv += _process_act_file(act_folder, "results.csv", IATIFileTypes.ACTIVITY_RESULTS_FILE,
                                       required=False, max_files=1, namespace=namespace)
    processed_csv += _process_act_file(act_folder, "activity_date.csv", IATIFileTypes.ACTIVITY_DATES_FILE,
                                       required=False, max_files=1, namespace=namespace)
    processed_csv += _process_act_file(act_folder, "contact_info.csv", IATIFileTypes.ACTIVITY_CONTACT_INFO_FILE,
                                       required=False, max_files=1, namespace=namespace)
    processed_csv += _process_act_file(act_folder, "descriptions.csv", IATIFileTypes.ACTIVITY_DESCRIPTIONS_FILE,
                                       required=False, max_files=1, namespace=namespace)

    # Generate the IATI Activities XML AFTER downloading files
    converter = IatiMultiCsvConverter()
    act_xml_filename = act_folder / ("iati-activities.xml" if namespace == DEFAULT_NAMESPACE
                                     else f"iati-activities-{namespace}.xml")

    converted = converter.csv_folder_to_xml(input_folder=act_folder, xml_output=act_xml_filename)
    log.info(f"Generated IATI Activities XML file: {act_xml_filename}, converted={converted}")

    return {
        "processed_csv": processed_csv,
        "converted": bool(converted),
        "xml_path": str(act_xml_filename),
    }


def _process_act_file(output_folder, filename, iati_file_type, required=True, max_files=1, namespace=DEFAULT_NAMESPACE):
    """Download CKAN resource to output_folder/filename for the given file_type & namespace."""
    log.info(f"Processing activities file: {iati_file_type}::{filename}")

    session = model.Session
    act_files = (
        session.query(IATIFile)
        .filter(IATIFile.file_type == iati_file_type.value)
        .filter(IATIFile.namespace == namespace)
        .all()
    )

    if len(act_files) == 0:
        if required:
            raise Exception(f"No activities IATI files {iati_file_type} found.")
        return 0

    if len(act_files) > max_files:
        raise Exception(
            f"Expected no more than {max_files} activities IATI file {iati_file_type}, found {len(act_files)}."
        )

    c = 0
    for iati_file in act_files:
        destination_path = output_folder / filename
        final_path = save_resource_data(iati_file.resource_id, str(destination_path))

        if not final_path:
            iati_file.track_processing(success=False, error_message="Failed to save resource data")
            continue

        iati_file.track_processing(success=True)
        c += 1
        log.info(f"Saved activity CSV data to {final_path}")

    return c
