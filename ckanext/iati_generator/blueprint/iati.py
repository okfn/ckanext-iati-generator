from flask import Blueprint, send_from_directory
import os
from ckan.lib import base
from ckan.lib.helpers import helper_functions as h
from ckan.plugins import toolkit
from ckanext.iati_generator.decorators import require_sysadmin_user
from ckanext.iati_generator.utils import create_or_update_iati_resource

iati_blueprint = Blueprint("iati_generator", __name__, url_prefix="/iati-dataset")


@iati_blueprint.route("/<package_id>", methods=["GET"])
@require_sysadmin_user
def iati_page(package_id):
    # Check configuration flag
    hide_tab = toolkit.asbool(toolkit.config.get("ckanext.iati_generator.hide_tab", False))
    if hide_tab:
        return toolkit.abort(404, toolkit._("Page disabled by configuration"))

    context = {"user": toolkit.c.user}
    # Fetch the package using package_show
    try:
        pkg_dict = toolkit.get_action("package_show")(context, {"id": package_id})
    except toolkit.ObjectNotFound:
        return toolkit.abort(404, toolkit._("Dataset not found"))

    # Pass both pkg and pkg_dict to the template (CKAN templates use both)
    ctx = {
        "pkg": pkg_dict,
        "pkg_dict": pkg_dict,
    }
    return base.render("iati/iati_page.html", ctx)


@iati_blueprint.route("/<package_id>/generate", methods=["POST"])
@require_sysadmin_user
def generate_test_iati(package_id):
    # Contexto mínimo para actions
    context = {"user": toolkit.c.user}

    # Recurso elegido en el formulario
    resource_id = toolkit.request.form.get("resource_id")
    if not resource_id:
        h.flash_error(toolkit._("Resource ID is required"), "error")
        return toolkit.redirect(toolkit.url_for("iati_generator.iati_page", package_id=package_id))

    # Dataset
    try:
        pkg = toolkit.get_action("package_show")(context, {"id": package_id})
    except Exception:
        h.flash_error(toolkit._("Dataset not found"), "error")
        return toolkit.redirect(toolkit.url_for("iati_generator.iati_page", package_id=package_id))

    # Recurso y sus extras (para namespace y tipo de referencia IATI)
    try:
        resource = toolkit.get_action("resource_show")(context, {"id": resource_id})
    except Exception:
        h.flash_error(toolkit._("Resource not found"), "error")
        return toolkit.redirect(toolkit.url_for("iati_generator.iati_page", package_id=package_id))

    # Normaliza extras -> dict
    res_extras_list = resource.get("extras", []) or []
    res_extras = {e.get("key"): e.get("value") for e in res_extras_list if isinstance(e, dict)}

    iati_namespace = (res_extras.get("iati_namespace") or "").strip()
    iati_file_reference = (res_extras.get("iati_file_reference") or "").strip()  # 'activities' | 'transactions' | 'multi' | ''

    # Llama a la action que genera el XML
    # Enviamos también namespace y file_reference (opcionales) para que el generador decida cómo interpretar el CSV
    logs = []
    try:
        result = toolkit.get_action("generate_iati_xml")(context, {
            "resource_id": resource_id,
            "iati_namespace": iati_namespace,
            "file_reference": iati_file_reference
        }) or {}
    except Exception as e:
        logs.append(f"❌ generate_iati_xml failed: {e}")
        result = {}

    # Extrae resultados
    xml_string = result.get("xml_string")
    resource_name = result.get("resource_name") or f"iati-{resource.get('name') or resource_id}.xml"
    logs.extend(result.get("logs", []))

    xml_url = None
    if not xml_string:
        # Falló la generación
        h.flash_error(toolkit._("Could not generate the XML file. Check the logs below."), "error")
    else:
        # ¿Ya existe un recurso XML asociado al dataset? (guardado en extras del dataset)
        pkg_extras_list = pkg.get("extras", []) or []
        pkg_extras = {e.get("key"): e.get("value") for e in pkg_extras_list if isinstance(e, dict)}
        existing_resource_id = pkg_extras.get("iati_base_resource_id")

        # Sube o actualiza el recurso XML en el dataset
        try:
            created = create_or_update_iati_resource(
                context=context,
                package_id=package_id,
                xml_string=xml_string,
                resource_name=resource_name,
                existing_resource_id=existing_resource_id
            )
        except Exception as e:
            logs.append(f"❌ upload failed: {e}")
            h.flash_error(toolkit._("Failed to upload the XML file."), "error")
            created = None

        if created:
            # Si no existía, guarda el id en extras del dataset
            if not existing_resource_id:
                try:
                    toolkit.get_action("package_patch")(context, {
                        "id": package_id,
                        "extras": [{"key": "iati_base_resource_id", "value": created["id"]}]
                    })
                except Exception as e:
                    logs.append(f"⚠️ could not persist iati_base_resource_id: {e}")

            # URL de descarga del XML
            # (puedes usar url_for si prefieres: toolkit.url_for('dataset_resource_download', id=package_id, resource_id=created['id']))
            xml_url = f"/dataset/{package_id}/resource/{created['id']}/download/{created['name']}"
            h.flash_success(toolkit._("XML file uploaded successfully."), "success")

    # Renderiza la misma página con logs y el link al XML si existe
    ctx = {
        "pkg": pkg,
        "pkg_dict": pkg,
        "logs": logs,
        "xml_url": xml_url,
        "selected_resource_id": resource_id,
    }
    return base.render("iati/iati_page.html", ctx)


@iati_blueprint.route("/static-iati/<resource_id>/<filename>")
@require_sysadmin_user
def serve_iati_file(resource_id, filename):
    """
    Serves a dynamically generated IATI XML file from CKAN's local storage.

    The expected file path is:
        /storage/resources/<first_3>/<next_3>/<resource_id>/<filename>

    This function allows generated XML files to be accessible via a public URL,
    without relying on `url_type="upload"` or a web server like NGINX.

    Requires the user to be authenticated as a sysadmin.
    """
    storage_root = toolkit.config.get("ckan.storage_path")
    dir_path = os.path.join(
        storage_root, "resources",
        resource_id[:3],
        resource_id[3:6],
        resource_id
    )
    file_path = os.path.join(dir_path, filename)

    if not os.path.isfile(file_path):
        return toolkit.abort(404, toolkit._("XML file not found"))
    # TODO check if CKAN FlaskApp -> MultiStaticFlask.send_static_file is a better option
    return send_from_directory(directory=dir_path, path=filename)
