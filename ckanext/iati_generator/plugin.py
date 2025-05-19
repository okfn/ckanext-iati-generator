
import logging
from ckan import plugins as p
from ckan.plugins import toolkit
from ckanext.iati_generator.actions.iati import iati_generate_test_xml
from ckanext.iati_generator.blueprint.iati import iati_blueprint

log = logging.getLogger(__name__)


class IatiGeneratorPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IBlueprint)
    p.implements(p.IActions)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "ckanext-iati-generator")

    def get_blueprint(self):
        return [
            iati_blueprint
        ]

    def get_actions(self):
        return {
            "iati_generate_test_xml": iati_generate_test_xml,
        }
