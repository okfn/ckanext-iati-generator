from flask import Blueprint, render_template
from ckan.plugins import toolkit
from ckanext.iati_generator.decorators import require_sysadmin_user

iati_blueprint = Blueprint("iati_generator", __name__, url_prefix="/iati-dataset")


@iati_blueprint.route("/<package_id>", methods=["GET"])
@require_sysadmin_user
def iati_page(package_id):
    context = {"user": toolkit.c.user}
    # Fetch the package using package_show
    try:
        pkg_dict = toolkit.get_action("package_show")(context, {"id": package_id})
    except toolkit.ObjectNotFound:
        return toolkit.abort(404, toolkit._("Dataset not found"))

    # Pass both pkg and pkg_dict to the template (CKAN templates use both)
    return render_template(
        "package/iati_page.html",
        pkg=pkg_dict,
        pkg_dict=pkg_dict
    )
