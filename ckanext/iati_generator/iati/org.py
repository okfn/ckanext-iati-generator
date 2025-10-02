import logging

# from okfn_iati.organisation_xml_generator import (
#     IatiOrganisationCSVConverter,
#     IatiOrganisationXMLGenerator,
# )

from ckanext.iati_generator.iati.resource import save_resource_data
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.models.iati_files import IATIFile


log = logging.getLogger(__name__)


def process_org_files(namespace, tmp_folder):
    """ Process all organization IATI files
        We return the number of files processed
    """

    org_folder = tmp_folder / "org"
    org_folder.mkdir(parents=True, exist_ok=True)

    org_files = IATIFile.query.filter(
        IATIFile.file_type == IATIFileTypes.ORGANIZATION_MAIN_FILE.value
    ).all()
    if not org_files:
        log.warning("No organization IATI files found to process.")
        return 0

    c = 0
    for iati_file in org_files:
        log.info(f"Processing IATI Organization file: {iati_file}")
        destination_path = tmp_folder / f"{namespace}-org-file-{c+1}.csv"
        final_path = save_resource_data(iati_file.resource_id, str(destination_path))
        if not final_path:
            log.error(f"Failed to fetch data for resource ID: {iati_file.resource_id}")
            continue
        c += 1
        log.info(f"Saved organization CSV data to {final_path}")

    return c
