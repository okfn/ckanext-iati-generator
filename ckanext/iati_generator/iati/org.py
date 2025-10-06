import logging

from okfn_iati.organisation_xml_generator import IatiOrganisationMultiCsvConverter

from ckanext.iati_generator.iati.resource import save_resource_data
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE, IATIFile


log = logging.getLogger(__name__)


def process_org_files(namespace, tmp_folder):
    """ Process all organization IATI files
        We return the number of files processed
    """

    org_folder = tmp_folder / f"org-{namespace}"
    org_folder.mkdir(parents=True, exist_ok=True)

    _process_org_file(org_folder, "organization.csv", IATIFileTypes.ORGANIZATION_MAIN_FILE, required=True, max_files=1)
    _process_org_file(org_folder, "names.csv", IATIFileTypes.ORGANIZATION_NAMES_FILE, required=False, max_files=1)
    # TODO implement other organization files when needed

    # We are ready to generate the Organization IATI XML file
    converter = IatiOrganisationMultiCsvConverter()
    if namespace == DEFAULT_NAMESPACE:
        org_xml_filename = org_folder / "iati-organization.xml"
    else:
        org_xml_filename = org_folder / f"iati-organization-{namespace}.xml"

    converted = converter.csv_folder_to_xml(input_folder=org_folder, xml_output=org_xml_filename)
    log.info(f"Generated IATI Organization XML file: {org_xml_filename}, converted={converted}")

    # TODO expose this XML file in a public URL. The only secure way to do this is to use a CKAN resource
    # local files won't work for multiple CKAN instances.


def _process_org_file(output_folder, filename, iati_file_type, required=True, max_files=1):
    """ Generic org file process
    """
    log.info(f"Processing organization file: {iati_file_type}::{filename}")
    org_files = IATIFile.query.filter(IATIFile.file_type == iati_file_type.value).all()
    # We expect only one organization main file, fail if not
    if len(org_files) == 0:
        if required:
            raise Exception(f"No organization IATI files {iati_file_type} found.")

    if len(org_files) > max_files:
        raise Exception(
            f"Expected no more than {max_files} organization IATI file {iati_file_type}, found {len(org_files)}."
        )

    c = 0
    for iati_file in org_files:
        log.info(f"Processing IATI Organization file: {iati_file}")
        destination_path = output_folder / filename
        final_path = save_resource_data(iati_file.resource_id, str(destination_path))

        if not final_path:
            log.error(f"Failed to fetch data for resource ID: {iati_file.resource_id}")
            error_message = "Failed to save resource data"
            iati_file.track_processing(success=False, error_message=error_message)
            continue
        c += 1
        log.info(f"Saved organization CSV data to {final_path}")

    return c
