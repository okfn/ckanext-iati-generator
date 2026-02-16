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
from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE

log = logging.getLogger(__name__)


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

    tmp_dir = tempfile.mkdtemp()

    _prepare_organisation_csv_folder(dataset, tmp_dir)

    required = h.required_organisation_csv_files()
    pre = h.validate_required_csv_folder(Path(tmp_dir), required)
    if pre:
        # IatiOrganisationMultiCsvConverter will produce an empty organisation.xml file if the input_folder is empty.
        # This it not what we want because the file is useless. For activities this validation is handled by the converter.
        # We check and return error to be coherent with IatiMultiCsvConverter.
        raise toolkit.ValidationError(pre)

    output_path = tmp_dir + "/organisation.xml"
    converter = IatiOrganisationMultiCsvConverter()
    success = converter.csv_folder_to_xml(input_folder=tmp_dir, xml_output=output_path)

    if not success:
        # Use the CKAN ValidationError formar for errors
        validation_errors = {'Organizacion XML errors': converter.latest_errors}
        log.warning("Error when generating the organisation.xml file.")
        raise toolkit.ValidationError(
            {"error_org_xml": validation_errors}
        )

    org_resource = None
    for res in dataset.get("resources", []):
        if int(res.get("iati_file_type") or 0) == IATIFileTypes.FINAL_ORGANIZATION_FILE.value:
            org_resource = res
            break

    # Using werkzeug FileStorage is the only way to get resource_create working (same as activities)
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

    if org_resource:
        res_dict["id"] = org_resource["id"]
        result = toolkit.get_action("resource_patch")({}, res_dict)
        log.info(f"Patched organisation.xml resource {org_resource['id']}.")
    else:
        res_dict["package_id"] = dataset["id"]
        result = toolkit.get_action("resource_create")({}, res_dict)
        log.info(f"Created new organisation.xml resource with id {result['id']}.")

    namespace = h.normalize_namespace(dataset.get("iati_namespace", DEFAULT_NAMESPACE))
    h.upsert_final_iati_file(
        resource_id=result["id"],
        namespace=namespace,
        file_type=IATIFileTypes.FINAL_ORGANIZATION_FILE.value,
        success=True,
    )

    # The resource should live in the same dataset as all the other IATI csv and must be of type: ACTIVITY_MAIN_FILE.

    shutil.rmtree(tmp_dir)
    return result


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

    tmp_dir = tempfile.mkdtemp()

    _prepare_activities_csv_folder(dataset, tmp_dir)

    required = h.required_activity_csv_files()
    pre = h.validate_required_csv_folder(Path(tmp_dir), required)
    if pre:
        raise toolkit.ValidationError(pre)

    output_path = tmp_dir + "/activity.xml"
    converter = IatiMultiCsvConverter()
    success = converter.csv_folder_to_xml(csv_folder=tmp_dir, xml_output=output_path, validate_output=True)

    if not success:
        log.warning(f"Could not generate activity file for dataset {dataset['name']} ({dataset['id']})")
        validation_errors = {'Activity XML errors': converter.latest_errors}
        # Is this the best way to handle this scenario?
        raise toolkit.ValidationError(
            {"error_activity_xml": validation_errors}
        )

    activity_resource = None
    for res in dataset["resources"]:
        if int(res["iati_file_type"]) == IATIFileTypes.FINAL_ACTIVITY_FILE.value:
            activity_resource = res
            break

    # Using werkzeug FileStorage is the only way I found to get the resource_create action working.
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
        result = toolkit.get_action("resource_patch")({}, res_dict)
        log.info(f"Patched activity.xml resource {result['id']}.")
    else:
        res_dict["package_id"] = dataset["id"]
        result = toolkit.get_action("resource_create")({}, res_dict)
        log.info(f"Created new activity.xml resource with id {result['id']}.")

    namespace = h.normalize_namespace(dataset.get("iati_namespace", DEFAULT_NAMESPACE))

    h.upsert_final_iati_file(
        resource_id=result["id"],
        namespace=namespace,
        file_type=IATIFileTypes.FINAL_ACTIVITY_FILE.value,
        success=True,
    )

    shutil.rmtree(tmp_dir)
    return result


def iati_get_dataset_by_namespace(context, data_dict):
    """
    Get the dataset associated with the given IATI namespace.
    """
    namespace = toolkit.get_or_bust(data_dict, "namespace")

    ns_raw = str(namespace).strip()
    ns_norm = h.normalize_namespace(ns_raw)

    context = dict(context or {})
    context.setdefault("ignore_auth", True)
    context.setdefault("user", "")

    session = model.Session

    q = (
        session.query(model.Package)
        .join(model.PackageExtra, model.PackageExtra.package_id == model.Package.id)
        .filter(model.Package.state == "active")
        .filter(model.PackageExtra.key == "iati_namespace")
        .filter(model.PackageExtra.value.in_([ns_raw, ns_norm]))
        .order_by(model.Package.metadata_created.asc())
    )

    pkgs = q.limit(2).all()

    if not pkgs:
        return None

    if len(pkgs) > 1:
        # “first wins” (coincide con tus tests que esperan eso)
        names = [p.name for p in pkgs]
        log.warning("Multiple datasets found for namespace=%s: %s. Using first one.", ns_norm, names)

    return toolkit.get_action("package_show")(context, {"id": pkgs[0].id})
