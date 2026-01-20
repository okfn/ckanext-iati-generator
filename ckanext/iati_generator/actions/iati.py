import io
import logging
import shutil
import tempfile
from pathlib import Path

from ckan import model
from ckan.lib.uploader import ResourceUpload
from ckan.plugins import toolkit
from okfn_iati import IatiMultiCsvConverter
from okfn_iati.organisation_xml_generator import IatiOrganisationMultiCsvConverter
from werkzeug.datastructures import FileStorage

from ckanext.iati_generator import helpers as h
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE, IATIFile

log = logging.getLogger(__name__)


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

    data_dict['file_type'] = h.normalize_file_type_strict(
        data_dict['file_type']
    )

    file = IATIFile(
        namespace=h.normalize_namespace(data_dict.get('namespace', DEFAULT_NAMESPACE)),
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

    updates = {}

    # namespace
    if 'namespace' in data_dict:
        updates['namespace'] = h.normalize_namespace(data_dict['namespace'])

    # file_type
    if 'file_type' in data_dict:
        updates['file_type'] = h.normalize_file_type_strict(data_dict['file_type'])

    # is_valid
    is_valid_present = 'is_valid' in data_dict
    if is_valid_present:
        v = data_dict['is_valid']
        if v is None:
            updates['is_valid'] = None
        else:
            try:
                updates['is_valid'] = toolkit.asbool(v)
            except (ValueError, TypeError):
                # invalid boolean
                raise toolkit.ValidationError({'is_valid': 'Invalid boolean'})

    # last_error (only if provided)
    if 'last_error' in data_dict:
        le = data_dict['last_error']
        if isinstance(le, str) and le.strip().lower() in ('', 'none', 'null'):
            le = None
        updates['last_error'] = le
    else:
        # if is_valid was set to True and last_error not provided, clear last_error
        if is_valid_present and updates.get('is_valid') is True:
            updates['last_error'] = None

    # apply updates
    for k, v in updates.items():
        setattr(file, k, v)

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


def _prepare_organisation_csv_folder(dataset, tmp_dir):
    """Copy IATI CSV files required to generate organisation.xml into a folder.

    TODO: This method only works if files are hosted in the same webserver (single VM deployments).
    For other architectures (K8s, AWS, etc) will need to be extended/reimplemented.
    """

    mapping = {
        "100": "organisations.csv",
        "110": "names.csv",
        "120": "budgets.csv",
        "130": "expenditures.csv",
        "140": "documents.csv",
    }

    for resource in dataset["resources"]:
        key = resource.get("iati_file_type", "")
        if key and key in mapping.keys():
            ru = ResourceUpload({"id": resource["id"]})
            filepath = ru.get_path(resource["id"])
            destination = tmp_dir + "/" + mapping[key]
            shutil.copy(filepath, destination)
    log.info(f"Finished preparing the CSV folder for the IATI Organisation converter. (Path: {tmp_dir})")


def iati_generate_organisation_xml(context, data_dict):
    """ Compile all organisation related CSVs into the organisation.xml file."""
    # Permissions: iati_auth.iati_generate_xml_files
    toolkit.check_access('iati_generate_xml_files', context, data_dict)

    # Create temporary folder for CSVs
    package_id = toolkit.get_or_bust(data_dict, "package_id")
    dataset = toolkit.get_action('package_show')({}, {"id": package_id})

    # Identify if the final resource already exists for error logging
    org_resource = None
    for res in dataset.get("resources", []):
        if res.get("iati_file_type") and int(res.get("iati_file_type") or 0) == IATIFileTypes.FINAL_ORGANIZATION_FILE.value:
            org_resource = res
            break

    tmp_dir = tempfile.mkdtemp()

    try:
        # Prepare temporary folder
        _prepare_organisation_csv_folder(dataset, tmp_dir)

        # Manual validation required by the organisation process
        if not Path(tmp_dir + "/organisations.csv").exists():
            raise toolkit.ValidationError("No organisations.csv file provided. IATI organisation.xml file cannot be generated.")

        output_path = tmp_dir + "/organisation.xml"
        converter = IatiOrganisationMultiCsvConverter()
        success = converter.csv_folder_to_xml(input_folder=tmp_dir, xml_output=output_path)

        if not success:
            raise Exception("Error when generating the organisation.xml file via the converter.")

        # Prepare file for CKAN
        with open(output_path, "rb") as f:
            stream = io.BytesIO(f.read())
        upload = FileStorage(stream=stream, filename="organisation.xml")

        res_dict = {
            "name": "organisation.xml",
            "url_type": "upload",
            "upload": upload,
            "iati_file_type": IATIFileTypes.FINAL_ORGANIZATION_FILE.value,
            "format": "XML",
        }

        # Save to CKAN
        if org_resource:
            res_dict["id"] = org_resource["id"]
            result = toolkit.get_action("resource_patch")(context, res_dict)
            log.info(f"Patched organisation.xml resource {org_resource['id']}.")
        else:
            res_dict["package_id"] = dataset["id"]
            result = toolkit.get_action("resource_create")(context, res_dict)
            log.info(f"Created new organisation.xml resource with id {result['id']}.")

        # SUCCESS LOG: Update the log in the DB
        h.update_iati_file_log(result['id'], success=True)

        return result

    except Exception as e:
        error_msg = str(e)
        log.error(f"Error in iati_generate_organisation_xml: {error_msg}")

        # ERROR LOG: Persist in the iati_files table
        if org_resource:
            h.update_iati_file_log(org_resource['id'], success=False, error_message=error_msg)

        # Propagate error for the interface
        if not isinstance(e, toolkit.ValidationError):
            raise toolkit.ValidationError(f"Organisation Generation Error: {error_msg}")
        raise e

    finally:
        # Absolute cleanup of temporary files
        if Path(tmp_dir).exists():
            shutil.rmtree(tmp_dir)


def _prepare_activities_csv_folder(dataset, tmp_dir):
    """Copy IATI CSV files required to create activity.xml into a folder.

    The okfn_iati tool expects all the csv files to live in a folder.

    TODO: This method only works if files are hosted in the same webserver (single VM deployments).
    For other architectures (K8s, AWS, etc) will need to be extended/reimplemented.
    """

    mapping = {
        "200": "activities.csv",
        "210": "participating_orgs.csv",
        "220": "sectors.csv",
        "230": "budgets.csv",
        "240": "transactions.csv",
        "250": "transaction_sectors.csv",
        "260": "locations.csv",
        "270": "documents.csv",
        "280": "results.csv",
        "290": "indicators.csv",
        "300": "indicator_periods.csv",
        "310": "activity_date.csv",
        "320": "contact_info.csv",
        "330": "conditions.csv",
        "340": "descriptions.csv",
        "350": "country_budget_items.csv",
    }

    for resource in dataset["resources"]:
        key = resource.get("iati_file_type", "")
        if key and key in mapping.keys():
            ru = ResourceUpload({"id": resource["id"]})
            filepath = ru.get_path(resource["id"])
            destination = tmp_dir + "/" + mapping[key]
            shutil.copy(filepath, destination)
    log.info(f"Finished preparing the CSV folder for the IATI converter. (Path: {tmp_dir})")


def iati_generate_activities_xml(context, data_dict):
    """Generates the xml of Activities from a multi-csv structure."""

    toolkit.check_access("iati_generate_xml_files", context, data_dict)

    package_id = toolkit.get_or_bust(data_dict, "package_id")
    dataset = toolkit.get_action('package_show')({}, {"id": package_id})

    # Identify if the final XML resource already exists to update its error log later
    activity_resource = None
    for res in dataset.get("resources", []):
        if res.get("iati_file_type") and int(res["iati_file_type"]) == IATIFileTypes.FINAL_ACTIVITY_FILE.value:
            activity_resource = res
            break

    tmp_dir = tempfile.mkdtemp()

    try:
        # Prepare files
        _prepare_activities_csv_folder(dataset, tmp_dir)

        output_path = tmp_dir + "/activity.xml"
        converter = IatiMultiCsvConverter()

        # Execute conversion
        success = converter.csv_folder_to_xml(csv_folder=tmp_dir, xml_output=output_path, validate_output=True)

        if not success:
            raise toolkit.ValidationError(
                "Activity.xml file could not be created probably due to missing mandatory files or corrupted data."
            )

        # If we reach here, the conversion was successful. Prepare the upload.
        with open(output_path, "rb") as f:
            stream = io.BytesIO(f.read())
        upload = FileStorage(stream=stream, filename="activity.xml")

        res_dict = {
            "name": "activity.xml",
            "url_type": "upload",
            "upload": upload,
            "iati_file_type": IATIFileTypes.FINAL_ACTIVITY_FILE.value,
            "format": "XML",
        }

        if activity_resource:
            res_dict["id"] = activity_resource["id"]
            result = toolkit.get_action("resource_patch")(context, res_dict)
            log.info(f"Patched activity.xml resource {result['id']}.")
        else:
            res_dict["package_id"] = dataset["id"]
            result = toolkit.get_action("resource_create")(context, res_dict)
            log.info(f"Created new activity.xml resource with id {result['id']}.")

        # SUCCESS LOG: Update the IATIFile model for this resource
        h.update_iati_file_log(result['id'], success=True)

        return result

    except Exception as e:
        error_msg = str(e)
        log.error(f"Error in iati_generate_activities_xml: {error_msg}")

        # ERROR LOG: If the resource already exists, save the error in the DB
        if activity_resource:
            h.update_iati_file_log(activity_resource['id'], success=False, error_message=error_msg)

        # Propagate error for the interface
        if not isinstance(e, toolkit.ValidationError):
            raise toolkit.ValidationError(f"IATI Generation Error: {error_msg}")
        raise e

    finally:
        # Clean up the temporary folder
        if Path(tmp_dir).exists():
            shutil.rmtree(tmp_dir)
