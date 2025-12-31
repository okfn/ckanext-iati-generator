import logging

from ckan.plugins import toolkit
from ckan import model
from sqlalchemy import func

from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE, IATIFile
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator import helpers as h


log = logging.getLogger(__name__)


@toolkit.side_effect_free
def list_datasets_with_iati(context, data_dict=None):
    """
    Returns all datasets that have a generated IATI resource,
    identified by the extra 'iati_base_resource_id'.
    Supports optional pagination via 'start' and 'rows'.
    """
    # Ensure data_dict is a dictionary
    data_dict = data_dict or {}

    # Extract parameters with default values
    start = data_dict.get("start", 0)
    rows = data_dict.get("rows", 100)

    search_result = toolkit.get_action("package_search")(context, {
        "q": "extras_iati_base_resource_id:[* TO *]",
        "start": start,
        "rows": rows,
        "sort": "metadata_modified desc"
    })

    return search_result["results"]


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
