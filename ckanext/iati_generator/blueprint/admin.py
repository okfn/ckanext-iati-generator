from flask import Blueprint

from ckan.plugins import toolkit
from ckanext.iati_generator.decorators import require_sysadmin_user
from ckanext.iati_generator.actions.iati import list_datasets_with_iati

iati_blueprint_admin = Blueprint("iati_generator_admin", __name__, url_prefix="/ckan-admin/iati")


@iati_blueprint_admin.route("/", methods=["GET"])
@require_sysadmin_user
def index():
    context = {"user": toolkit.c.user}
    datasets = list_datasets_with_iati(context)
    return toolkit.render("iati/admin.html", {"datasets": datasets})
