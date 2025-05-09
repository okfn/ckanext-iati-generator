from flask import Blueprint, render_template
from ckan.plugins import toolkit

iati_blueprint = Blueprint("iati_generator", __name__, url_prefix="/iati-dataset")


@iati_blueprint.route("/<package_id>", methods=["GET"])
def iati_page(package_id):
    context = {"user": toolkit.c.user}
    toolkit.check_access("sysadmin", context)
    return render_template("package/iati_page.html", pkg_id=package_id)
