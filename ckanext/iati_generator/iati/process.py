"""
Process all availabe IATIFiles and generate IATI XML files
Go through all IATIFile entries by type and process the related CKAN resource
"""
from pathlib import Path
import logging


from ckanext.iati_generator.iati.org import process_org_files


log = logging.getLogger(__name__)


def process_iati_files():
    """ Process all IATI files
        We must save all CSV files into folder to process later
    """

    namespace = "iati-xml"
    # TODO allow multiple namespaces with a new field in the IATIFile model
    # Use the folder ckanext/iati_generator/tmp/ to save the CSV files
    tmp_folder = Path(__file__).parent / "tmp"
    tmp_folder.mkdir(parents=True, exist_ok=True)
    # activities_folder = tmp_folder / "activities"
    # activities_folder.mkdir(parents=True, exist_ok=True)

    # ============ ORGANIZATION FILEs ================================
    processed_files = process_org_files(namespace, tmp_folder)
    log.info(f"Processed {processed_files} organization IATI files.")
    # ============ ACTIVITIES FILEs ================================
    # TODO implement process_activities_files()
