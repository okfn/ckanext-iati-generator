import logging
import tempfile
import shutil
from pathlib import Path

from ckan.plugins import toolkit
from ckan.lib.uploader import ResourceUpload
from ckan import model
from sqlalchemy import func
from okfn_iati.organisation_xml_generator import IatiOrganisationMultiCsvConverter
from okfn_iati import IatiMultiCsvConverter

from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE, IATIFile
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator import helpers as h


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
        namespace=data_dict.get('namespace', DEFAULT_NAMESPACE),
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
        updates['namespace'] = data_dict['namespace']

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


@toolkit.side_effect_free
def iati_file_list(context, data_dict=None):
    """
    Paginated list of IATI files (IATIFile records joined with Resource/Package).

    Parameters (data_dict keys):
      - start (int, optional): Offset for pagination. Default: 0.
      - rows (int, optional): Page size. Default: 100.
      - namespace (str, optional): Filter by namespace (e.g. "iati-xml", "iati-country-a", "iati-country-b").
      - file_type (str|int, optional): IATI file type filter. Accepts Enum name
        (e.g. "ORGANIZATION_MAIN_FILE") or the corresponding integer value.
      - owner_org (str, optional): Filter by owning organization id (dataset.owner_org).
      - package_id (str, optional): Filter by a specific dataset id.
      - resource_id (str, optional): Filter by a specific resource id.
      - valid (str|bool|int, optional): Filter by validity. Truthy values: "true", "1", "yes";
        Falsy values: "false", "0", "no". Case-insensitive.

    Returns:
      dict: {
        "count": <int total_without_pagination>,
        "results": [
          {
            "id": <iati_file_id>,
            "namespace": "<str>",
            "file_type": "<ENUM_NAME>",
            "is_valid": <bool>,
            "last_success": "YYYY-MM-DD" | null,
            "last_error": "<str | null>",
            "resource": {
              "id": "<str>",
              "name": "<str>",
              "format": "<str>",
              "url": "<str>",
              "description": "<str | null>"
            },
            "dataset": {
              "id": "<str>",
              "name": "<str>",
              "title": "<str>",
              "owner_org": "<str>"
            }
          }, ...
        ]
      }

    Usage examples:
      toolkit.get_action("iati_file_list")(context, {"start": 0, "rows": 20})
      toolkit.get_action("iati_file_list")(context, {"file_type": "ORGANIZATION_MAIN_FILE"})
      toolkit.get_action("iati_file_list")(context, {"valid": "true", "owner_org": "<org_id>"})
      toolkit.get_action("iati_file_list")(context, {"namespace": "iati-xml"})
    """
    data_dict = data_dict or {}
    toolkit.check_access("iati_file_list", context, data_dict)

    start = int(data_dict.get("start", 0) or 0)
    rows = int(data_dict.get("rows", 100) or 100)

    Session = model.Session
    Resource = model.Resource
    Package = model.Package

    q_base = (
        Session.query(
            IATIFile.id.label("iati_id"),
            IATIFile.namespace.label("namespace"),
            IATIFile.file_type.label("file_type"),
            IATIFile.is_valid.label("is_valid"),
            IATIFile.last_processed_success.label("last_success"),
            IATIFile.last_error.label("last_error"),

            Resource.id.label("resource_id"),
            Resource.name.label("resource_name"),
            Resource.url.label("resource_url"),
            Resource.format.label("resource_format"),
            Resource.description.label("resource_description"),
            Resource.package_id.label("package_id"),

            Package.name.label("package_name"),
            Package.title.label("package_title"),
            Package.owner_org.label("owner_org"),
        )
        .join(Resource, Resource.id == IATIFile.resource_id)
        .join(Package, Resource.package_id == Package.id)
        .filter(Resource.state == "active", Package.state == "active")
    )

    # -------- optional filters
    if data_dict.get("resource_id"):
        q_base = q_base.filter(Resource.id == data_dict["resource_id"])

    if data_dict.get("package_id"):
        q_base = q_base.filter(Resource.package_id == data_dict["package_id"])

    if data_dict.get("owner_org"):
        q_base = q_base.filter(Package.owner_org == data_dict["owner_org"])

    # --- namespace filter
    if data_dict.get("namespace"):
        q_base = q_base.filter(IATIFile.namespace == data_dict["namespace"])

    if "valid" in data_dict and data_dict["valid"] is not None:
        val = str(data_dict["valid"]).lower() in ("true", "1", "yes")
        q_base = q_base.filter(IATIFile.is_valid == val)

    # --- file_type filter
    if data_dict.get("file_type") is not None:
        ft = h.normalize_file_type_strict(data_dict["file_type"])
        q_base = q_base.filter(IATIFile.file_type == ft)

    # -------- total count without pagination
    count_q = Session.query(func.count()).select_from(q_base.subquery())
    total = count_q.scalar() or 0

    # -------- ordering + pagination
    q = q_base.order_by(Package.name.asc(), Resource.name.asc()).offset(start).limit(rows)

    file_type_map = {e.value: e.name for e in IATIFileTypes}

    results = []
    for r in q.all():
        # map file_type int to enum name
        file_type_label = file_type_map.get(
            r.file_type,
            str(r.file_type or "")
        )

        results.append({
            "id": r.iati_id,
            "namespace": r.namespace,
            "file_type": file_type_label,
            "is_valid": bool(r.is_valid),
            "last_success": r.last_success.isoformat() if getattr(r, "last_success", None) else None,
            "last_error": r.last_error,

            "resource": {
                "id": r.resource_id,
                "name": r.resource_name or r.resource_id,
                "format": r.resource_format,
                "url": r.resource_url,
                "description": r.resource_description,
            },
            "dataset": {
                "id": r.package_id,
                "name": r.package_name,
                "title": r.package_title,
                "owner_org": r.owner_org,
            },
        })

    return {"count": total, "results": results}


@toolkit.side_effect_free
def iati_resources_list(context, data_dict=None):
    """
    Return a list of resources with IATIFile records, including dataset info.
    This fn returns ALL resources with IATIFile, no pagination.

    Each row contains:
      - namespace
      - resource: {...}
      - dataset: {...}
      - iati_file: IATIFile.as_dict()
    """
    data_dict = data_dict or {}
    toolkit.check_access("iati_file_list", context, data_dict)

    namespace_filter = data_dict.get("namespace")

    files_by_resource = h.iati_files_by_resource(namespace=namespace_filter)

    results = []
    datasets = {}

    for resource_id, iati_file in files_by_resource.items():

        # resource
        res = toolkit.get_action("resource_show")(context, {"id": resource_id})
        package_id = res["package_id"]

        # dataset (cache to avoid multiple calls)
        if package_id not in datasets:
            pkg = toolkit.get_action("package_show")(context, {"id": package_id})
            datasets[package_id] = pkg
        else:
            pkg = datasets[package_id]

        iati_dict = iati_file.as_dict()

        results.append({
            "namespace": iati_dict.get("namespace"),
            "resource": res,
            "dataset": pkg,
            "iati_file": iati_dict,
        })

    # Sort by dataset.name, then resource.name, then file_type
    results.sort(
        key=lambda r: (
            (r["namespace"] or "").lower(),
            (r["iati_file"]["file_type"] or ""),
        )
    )

    return {
        "count": len(results),
        "results": results,
    }


def _get_owner_org_id(context, data_dict):
    """Get or infer owner_org_id from data_dict or user permissions."""
    owner_org_id = data_dict.get("owner_org")

    if not owner_org_id:
        orgs = toolkit.get_action("organization_list_for_user")(context, {"permission": "admin"})
        if orgs:
            owner_org_id = orgs[0]["id"]

    if not owner_org_id:
        raise toolkit.ValidationError(
            {"owner_org": "Missing owner_org and could not infer it from user permissions"}
        )

    return owner_org_id


def _get_final_org_record(owner_org_id, namespace):
    """Fetch the FINAL_ORGANIZATION_FILE record for the given org and namespace."""
    Session = model.Session
    Resource = model.Resource
    Package = model.Package

    final_record = (
        Session.query(IATIFile)
        .join(Resource, Resource.id == IATIFile.resource_id)
        .join(Package, Package.id == Resource.package_id)
        .filter(
            Package.owner_org == owner_org_id,
            Package.state == "active",
            Resource.state == "active",
            IATIFile.file_type == IATIFileTypes.FINAL_ORGANIZATION_FILE.value,
            IATIFile.namespace == namespace,
        )
        .first()
    )

    if not final_record:
        raise toolkit.ObjectNotFound(
            f"No destination resource (FINAL_ORGANIZATION_FILE) found for owner_org={owner_org_id} ns={namespace}"
        )

    return final_record


def _process_org_csv_files(context, org_folder, namespace, owner_org_id, final_record):
    """Process all organization CSV file types and download to org_folder."""
    file_types_mapping = {
        IATIFileTypes.ORGANIZATION_MAIN_FILE: ("organization.csv", True, 1),
        IATIFileTypes.ORGANIZATION_NAMES_FILE: ("names.csv", False, 1),
        IATIFileTypes.ORGANIZATION_BUDGET_FILE: ("budgets.csv", False, None),
        IATIFileTypes.ORGANIZATION_EXPENDITURE_FILE: ("expenditures.csv", False, None),
        IATIFileTypes.ORGANIZATION_DOCUMENT_FILE: ("documents.csv", False, None),
    }

    files_processed = 0
    for file_type, (filename, required, max_files) in file_types_mapping.items():
        try:
            count = h.process_org_file_type(
                context=context,
                output_folder=org_folder,
                filename=filename,
                file_type=file_type,
                namespace=namespace,
                owner_org_id=owner_org_id,
                required=required,
                max_files=max_files,
            )
            files_processed += count
            log.info("Processed %s file(s) for %s", count, file_type.name)
        except Exception as e:
            log.error("Error processing %s: %s", file_type.name, e)
            if required:
                try:
                    final_record.track_processing(success=False, error_message=str(e))
                except Exception:
                    pass
                raise

    return files_processed


def _convert_org_xml(org_folder, namespace, owner_org_id, files_processed, final_record):
    """Convert organization CSV files to XML and return the path."""
    if files_processed == 0:
        msg = f"No organization CSV files found for owner_org={owner_org_id} ns={namespace}"
        log.warning(msg)
        try:
            final_record.track_processing(success=False, error_message=msg)
        except Exception:
            pass
        return None

    converter = IatiOrganisationMultiCsvConverter()

    xml_filename = (
        org_folder / "iati-organization.xml"
        if namespace == DEFAULT_NAMESPACE
        else org_folder / f"iati-organization-{namespace}.xml"
    )

    log.info("Converting Organization CSV folder to XML: %s", xml_filename)

    converted = converter.csv_folder_to_xml(
        input_folder=str(org_folder),
        xml_output=str(xml_filename),
    )

    if not converted or not xml_filename.exists():
        msg = f"Failed to generate organization XML for owner_org={owner_org_id} ns={namespace}"
        log.error(msg)
        try:
            final_record.track_processing(success=False, error_message=msg)
        except Exception:
            pass
        return None

    return xml_filename


def generate_organization_xml(context, data_dict):
    """
    Generate IATI Organization XML for a given organization.

    Parameters (data_dict keys):
      - namespace (str, optional): Namespace for the IATI file. Default: DEFAULT_NAMESPACE.
      - owner_org (str, optional but recommended): Organization id. If not provided, inferred from user.

    Behavior (matches TODO/docstring):
      - Fetch all organization IATIFiles for the given owner_org+namespace.
      - Require the FINAL_ORGANIZATION_FILE destination resource for that owner_org+namespace.
      - Download the CSVs to a temporary folder org-<namespace>.
      - Run IatiOrganisationMultiCsvConverter.csv_folder_to_xml on that folder.
      - Update the resource related to the FINAL_ORGANIZATION_FILE with the final XML.

    Returns:
      dict: {
        "success": <bool>,
        "message": <str>,
        "files_processed": <int>
      }
    """
    toolkit.check_access("generate_organization_xml", context, data_dict)

    namespace = h.normalize_namespace(data_dict.get("namespace", DEFAULT_NAMESPACE))
    owner_org_id = _get_owner_org_id(context, data_dict)

    log.info("Generating IATI Organization XML (owner_org=%s ns=%s)", owner_org_id, namespace)

    final_record = _get_final_org_record(owner_org_id, namespace)

    with tempfile.TemporaryDirectory() as tmp_dir:
        org_folder = Path(tmp_dir) / f"org-{namespace}"
        org_folder.mkdir(parents=True, exist_ok=True)

        files_processed = _process_org_csv_files(context, org_folder, namespace, owner_org_id, final_record)

        xml_filename = _convert_org_xml(org_folder, namespace, owner_org_id, files_processed, final_record)

        if not xml_filename:
            return {
                "success": False,
                "message": f"No organization CSV files found for owner_org={owner_org_id} ns={namespace}",
                "files_processed": files_processed
            }

        # Upload to destination resource
        with open(xml_filename, "rb") as f:
            toolkit.get_action("resource_patch")(context, {
                "id": final_record.resource_id,
                "upload": f,
                "format": "XML",
                "url_type": "upload",
            })

        try:
            final_record.track_processing(success=True)
        except Exception:
            pass

        return {
            "success": True,
            "message": "Organization XML generated and uploaded successfully",
            "files_processed": files_processed,
        }


def _prepare_activities_csv_folder(dataset, tmp_dir):
    """Copy all IATI CSV files into a folder for okfn_iati to process.

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
    """Generates the XML of Activities from a multi-csv structure.

    Parameters (data_dict keys):
      - package_id (str): dataset id/name
      - namespace (str, optional): namespace, defaults to DEFAULT_NAMESPACE

    Behavior:
      - Prepare csv folder (local files)
      - Convert csv→xml (validate_output=True)
      - CREATE the ACTIVITY_MAIN_FILE XML resource + IATIFile if missing, else UPDATE it
      - Track processing on the IATIFile record
    """
    toolkit.check_access("iati_generate_activities_xml", context, data_dict)

    package_id = toolkit.get_or_bust(data_dict, "package_id")
    namespace = h.normalize_namespace(data_dict.get("namespace", DEFAULT_NAMESPACE))

    dataset = toolkit.get_action("package_show")(context, {"id": package_id})

    Session = model.Session
    Resource = model.Resource

    main_file_record = (
        Session.query(IATIFile)
        .join(Resource, Resource.id == IATIFile.resource_id)
        .filter(
            Resource.package_id == package_id,
            Resource.state == "active",
            IATIFile.file_type == IATIFileTypes.ACTIVITY_MAIN_FILE.value,
            IATIFile.namespace == namespace,
        )
        .first()
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = Path(tmp_dir) / "activity.xml"

        try:
            _prepare_activities_csv_folder(dataset, tmp_dir)

            converter = IatiMultiCsvConverter()
            converter.csv_folder_to_xml(
                csv_folder=tmp_dir,
                xml_output=str(output_path),
                validate_output=True,
            )

            if not output_path.exists():
                raise toolkit.ValidationError({"xml": "Converter did not produce output activity.xml"})

            # CREATE if missing, else UPDATE
            if main_file_record:
                # UPDATE
                with open(output_path, "rb") as f:
                    toolkit.get_action("resource_patch")(context, {
                        "id": main_file_record.resource_id,
                        "upload": f,
                        "format": "XML",
                        "url_type": "upload",
                    })
            else:
                # CREATE resource + IATIFile
                name = "iati-activity.xml" if namespace == DEFAULT_NAMESPACE else f"iati-activity-{namespace}.xml"
                with open(output_path, "rb") as f:
                    new_res = toolkit.get_action("resource_create")(context, {
                        "package_id": package_id,
                        "name": name,
                        "format": "XML",
                        "upload": f,
                        "url_type": "upload",
                        "description": "Generated IATI Activities XML",
                    })

                # create IATIFile record
                main_file_record = IATIFile(
                    namespace=namespace,
                    file_type=IATIFileTypes.ACTIVITY_MAIN_FILE.value,
                    resource_id=new_res["id"],
                )
                main_file_record.save()

            try:
                main_file_record.track_processing(success=True)
            except Exception:
                pass

            return {"success": True, "resource_id": main_file_record.resource_id}

        except Exception as e:
            log.error("Error generating activities XML for %s (ns=%s): %s", package_id, namespace, e)

            if main_file_record:
                try:
                    main_file_record.track_processing(success=False, error_message=str(e))
                except Exception:
                    pass

            raise
