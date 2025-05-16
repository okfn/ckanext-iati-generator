
import logging
from ckanext.iati_generator.blueprint.iati import iati_blueprint
from ckan import plugins as p
from ckan.plugins import toolkit

log = logging.getLogger(__name__)


class IatiGeneratorPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IBlueprint)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "ckanext-iati-generator")

    def get_blueprint(self):
        return [
            iati_blueprint
        ]
