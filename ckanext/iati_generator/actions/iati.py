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
    try:
        # accepts int, numeric string ("100"), or enum name ("ORGANIZATION_MAIN_FILE")
        ft = data_dict['file_type']
        if isinstance(ft, str):
            if ft.isdigit():
                data_dict['file_type'] = int(ft)
                _ = IATIFileTypes(data_dict['file_type'])  # value
            else:
                data_dict['file_type'] = IATIFileTypes[ft].value
        else:
            _ = IATIFileTypes(ft)  # validates existence
    except Exception:
        raise toolkit.ValidationError({'file_type': 'Invalid IATIFileTypes value'})

    data_dict['file_type'] = _normalize_file_type(data_dict['file_type'])

    file = IATIFile(
        namespace=data_dict.get('namespace', DEFAULT_NAMESPACE),
        file_type=data_dict['file_type'],
        resource_id=data_dict['resource_id'],
    )
    file.save()
    return toolkit.get_action('iati_file_show')(context, {'id': file.id})


# --- normalize inputs ---

def _normalize_file_type(value):
    """
    Normalize file_type input to its integer value.
    Accepts Enum name (str) or integer value.
    Raises ValidationError if invalid.
    """
    try:
        ft = value
        if isinstance(ft, str):
            if ft.isdigit():
                ft = int(ft)
                _ = IATIFileTypes(ft)
            else:
                ft = IATIFileTypes[ft].value
        else:
            _ = IATIFileTypes(ft)
        return int(ft)
    except (KeyError, ValueError, TypeError):
        raise toolkit.ValidationError({'file_type': 'Invalid IATIFileTypes value'})


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
        updates['file_type'] = _normalize_file_type(data_dict['file_type'])

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

    if "valid" in data_dict and data_dict["valid"] is not None:
        val = str(data_dict["valid"]).lower() in ("true", "1", "yes")
        q_base = q_base.filter(IATIFile.is_valid == val)

    if data_dict.get("file_type") is not None:
        ft = data_dict["file_type"]
        try:
            # accepts enum name or int
            if isinstance(ft, str) and not ft.isdigit():
                ft = IATIFileTypes[ft].value
            else:
                ft = int(ft)
            _ = IATIFileTypes(ft)  # validates existence
            q_base = q_base.filter(IATIFile.file_type == ft)
        except Exception:
            raise toolkit.ValidationError({"file_type": "Invalid IATIFileTypes value"})

    # -------- total count without pagination
    count_q = Session.query(func.count()).select_from(q_base.subquery())
    total = count_q.scalar() or 0

    # -------- ordering + pagination
    q = q_base.order_by(Package.name.asc(), Resource.name.asc()).offset(start).limit(rows)

    results = []
    for r in q.all():
        try:
            file_type_label = IATIFileTypes(r.file_type).name
        except Exception:
            file_type_label = str(r.file_type or "")

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

    Returns items with the following structure:
      {
        "namespace": ...,
        "resource": {...},
        "dataset": {...},
        "iati_file": {
            "file_type": ...,
            "is_valid": ...,
            "last_processed_success": ...,
            "last_error": ...,
        },
      }

    The admin blueprint then flattens this for the template.
    """
    data_dict = data_dict or {}
    toolkit.check_access("iati_file_list", context, data_dict)

    # Índice: (resource_id, namespace, file_type_int) -> IATIFile
    iati_index = h.build_iati_index()
    files = list(iati_index.values())

    results = []

    resources_cache = {}
    datasets_cache = {}

    for f in files:
        resource_id = f.resource_id

        # ---- resource
        res = resources_cache.get(resource_id)
        if not res:
            try:
                res = toolkit.get_action("resource_show")(context, {"id": resource_id})
            except toolkit.ObjectNotFound:
                log.warning(
                    "IATIFile %s references missing resource %s", f.id, resource_id
                )
                continue
            resources_cache[resource_id] = res

        # ---- dataset
        package_id = res["package_id"]
        pkg = datasets_cache.get(package_id)
        if not pkg:
            try:
                pkg = toolkit.get_action("package_show")(context, {"id": package_id})
            except toolkit.ObjectNotFound:
                log.warning(
                    "IATIFile %s references missing package %s", f.id, package_id
                )
                continue
            datasets_cache[package_id] = pkg

        # ---- file_type + namespace
        ft_int = f.file_type
        label, ft_int_norm = h.normalize_file_type(ft_int)
        if ft_int_norm is not None:
            ft_int = ft_int_norm

        ns = f.namespace or DEFAULT_NAMESPACE

        # ---- fila “candidate” con info de validación
        candidate = h.build_candidate_row(pkg, res, label, ns, ft_int, iati_index)

        # Adapt to the format expected by the blueprint
        iati_file_info = {
            "file_type": candidate["file_type"],
            "is_valid": candidate["is_valid"],
            "last_processed_success": candidate["last_success"],
            "last_error": candidate["last_error"],
        }

        item = {
            "namespace": candidate["namespace"],
            "resource": candidate["resource"],
            "dataset": candidate["dataset"],
            "iati_file": iati_file_info,
        }
        results.append(item)

    # sort similar to iati_file_list
    results.sort(
        key=lambda item: (
            item["dataset"]["name"],
            item["resource"]["name"],
            item["iati_file"]["file_type"],
        )
    )

    return {
        "count": len(results),
        "results": results,
    }
