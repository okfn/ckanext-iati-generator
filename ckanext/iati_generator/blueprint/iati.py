from flask import Blueprint, render_template
from ckan.plugins import toolkit

iati_blueprint = Blueprint("iati_generator", __name__, url_prefix="/dataset")


@iati_blueprint.route("/<id>/iati", methods=["GET"])
def iati_page(id):
    context = {"model": toolkit.model, "session": toolkit.model.Session, "user": toolkit.c.user}
    toolkit.check_access("sysadmin", context)
    return render_template("package/iati_page.html", pkg_id=id)
