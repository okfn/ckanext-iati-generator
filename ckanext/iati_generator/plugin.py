
import logging
from ckan import plugins as p
from ckan.plugins import toolkit
from ckanext.iati_generator.actions.iati import generate_iati_xml
from ckan.lib.plugins import DefaultTranslation
from ckanext.iati_generator.blueprint.iati import iati_blueprint
from ckanext.iati_generator.blueprint.admin import iati_blueprint_admin

log = logging.getLogger(__name__)


class IatiGeneratorPlugin(p.SingletonPlugin, DefaultTranslation):
    p.implements(p.IConfigurer)
    p.implements(p.IBlueprint)
    p.implements(p.IActions)
    p.implements(p.ITranslation)
    p.implements(p.ITemplateHelpers)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "ckanext-iati-generator")

    def get_blueprint(self):
        return [
            iati_blueprint,
            iati_blueprint_admin
        ]

    def get_actions(self):
        return {
            "generate_iati_xml": generate_iati_xml,
        }

    def i18n_locales(self):
        """Languages this plugin has translations for."""
        return ["es", "en"]

    def i18n_domain(self):
        """The domain for the translation files."""
        # Return the domain for the translation files.
        return "ckanext-iati-generator"

    def get_helpers(self):
        """Return a dictionary of helper functions."""
        return {
            "iati_tab_enabled": lambda: not toolkit.asbool(
                toolkit.config.get("ckanext.iati_generator.hide_tab", False)
            )
        }
