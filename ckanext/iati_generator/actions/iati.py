import logging
import csv

from ckan.plugins import toolkit
from ckan import model
from sqlalchemy import func

from ckanext.iati_generator.csv import row_to_iati_activity
from ckanext.iati_generator.utils import generate_final_iati_xml, get_resource_file_path
from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE, IATIFile
from ckanext.iati_generator.models.enums import IATIFileTypes


log = logging.getLogger(__name__)


def get_validated_csv_data(context, resource_id):
    logs = []
    resource_name = None
    activities = []
    errored_rows = 0

    # Validate existence of the resource and get its name
    resource = toolkit.get_action("resource_show")(context, {"id": resource_id})
    resource_name = resource.get("name", "resource")

    # Validate file type and get path
    path = get_resource_file_path(context, resource_id)
    logs.append(f"Reading CSV at: {path}")

    # Read CSV and validate headers
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        log.info(f"CSV headers: {fieldnames}")
        logs.append(f"CSV headers: {fieldnames}")

        required_fields = ["iati_identifier", "reporting_org_ref", "reporting_org_type", "reporting_org_name", "title"]
        missing = [field for field in required_fields if field not in fieldnames]

        if missing:
            raise ValueError(f"Missing required columns in CSV header: {', '.join(missing)}")

        ROWS_LIMIT = int(toolkit.config.get("ckanext.iati_generator.rows_limit", 50000))
        MAX_ALLOWED_FAILURES = int(toolkit.config.get("ckanext.iati_generator.max_allowed_failures", 10))

        for i, row in enumerate(reader):
            if i >= ROWS_LIMIT:
                logs.append(f"Row limit reached ({ROWS_LIMIT}); stopping")
                break
            try:
                activity = row_to_iati_activity(row)
                activities.append(activity)
            except Exception as e:
                msg = f"Row {i+1}: error ({e}); skipping."
                logs.append(msg)
                log.error(msg)
                errored_rows += 1
                if errored_rows > MAX_ALLOWED_FAILURES:
                    logs.append(f"Max allowed failures reached ({MAX_ALLOWED_FAILURES}); stopping")
                    break

    return activities, logs, resource_name


def generate_iati_xml(context, data_dict):
    """
    Generate an IATI XML string from a CSV resource file.

    data_dict should contain:
        - resource_id: the ID of the resource to read from

    Returns a dict with:
        - xml_string: the generated IATI XML as a string, or None if failed
        - logs: a list of logs generated during the process
        - resource_name: the name of the resource being processed (or None)
        - error: in case of failure, an error message
    """
    logs = []
    resource_id = data_dict.get("resource_id")
    logs.append(f"Start generating IATI XML file for resource: {resource_id}")

    try:
        activities, csv_logs, resource_name = get_validated_csv_data(context, resource_id)
    except Exception as e:
        msg = f"Error validating CSV data: {e}"
        log.error(msg)
        logs.append(msg)
        return {"xml_string": None, "logs": logs, "resource_name": None, "error": msg}

    logs.extend(csv_logs)
    if not activities:
        error = "No valid activities found in the CSV file"
        logs.append(error)
        return {"xml_string": None, "logs": logs, "resource_name": resource_name, "error": error}

    try:
        xml_string = generate_final_iati_xml(activities)
    except Exception as e:
        msg = f"Error during IATI generation: {e}"
        log.error(msg)
        logs.append(msg)
        return {"xml_string": None, "logs": logs, "resource_name": None, "error": msg}

    logs.append(f"IATI XML generated successfully for file: {resource_name}")
    return {"xml_string": xml_string, "logs": logs, "resource_name": resource_name, "error": None}


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
        # acepta int o nombre del enum
        ft = data_dict['file_type']
        if isinstance(ft, str):
            data_dict['file_type'] = IATIFileTypes[ft].value
        else:
            _ = IATIFileTypes(ft)  # valida que exista
    except Exception:
        raise toolkit.ValidationError({'file_type': 'Invalid IATIFileTypes value'})

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

    for key in ['namespace', 'file_type', 'is_valid', 'last_error']:
        if key in data_dict:
            setattr(file, key, data_dict[key])

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
    Listado paginado de 'IATI files' (registros IATIFile unidos a Resource/Package).

    Parámetros (opcionales):
      - start: int (default 0)
      - rows: int (default 100)
      - file_type: puede ser nombre del enum (p.ej. 'ORGANIZATION_MAIN_FILE') o int
      - owner_org: id de la organización (filtra por datasets del owner_org)
      - package_id: id del dataset (filtra por un dataset concreto)
      - resource_id: id del recurso (filtra por un recurso concreto)
      - valid: 'true'/'false' (filtra por IATIFile.is_valid)

    Respuesta:
      {
        "count": <total_sin_paginación>,
        "results": [
          {
            "id": <iati_file_id>,
            "namespace": "...",
            "file_type": "<NOMBRE_ENUM>",
            "is_valid": true/false,
            "last_success": "YYYY-MM-DD" | null,
            "last_error": "mensaje" | null,
            "resource": {
              "id": "...",
              "name": "...",
              "format": "...",
              "url": "...",
              "description": "..."
            },
            "dataset": {
              "id": "...",
              "name": "...",
              "title": "...",
              "owner_org": "..."
            }
          },
          ...
        ]
      }
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

    # -------- filtros opcionales
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
            # admite nombre del enum o int
            if isinstance(ft, str) and not ft.isdigit():
                ft = IATIFileTypes[ft].value
            else:
                ft = int(ft)
            _ = IATIFileTypes(ft)  # valida
            q_base = q_base.filter(IATIFile.file_type == ft)
        except Exception:
            raise toolkit.ValidationError({"file_type": "Invalid IATIFileTypes value"})

    # -------- conteo total sin paginar
    count_q = Session.query(func.count()).select_from(q_base.subquery())
    total = count_q.scalar() or 0

    # -------- orden + paginación
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
