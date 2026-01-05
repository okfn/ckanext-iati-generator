
import logging
from ckan import plugins as p
from ckan.plugins import toolkit
from ckanext.iati_generator.actions import iati as iati_actions
from ckanext.iati_generator.actions import resources as resources_actions
from ckanext.iati_generator.auth import iati as iati_auth
from ckan.lib.plugins import DefaultTranslation
from ckanext.iati_generator.blueprint.admin import iati_file_admin
from ckanext.iati_generator.blueprint.public_iati import iati_public
from ckanext.iati_generator import helpers as h


log = logging.getLogger(__name__)


class IatiGeneratorPlugin(p.SingletonPlugin, DefaultTranslation):
    p.implements(p.IConfigurer)
    p.implements(p.IBlueprint)
    p.implements(p.IActions)
    p.implements(p.ITranslation)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IAuthFunctions)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "iati_generator")

    def get_blueprint(self):
        return [
            iati_file_admin,
            iati_public,
        ]

    def get_actions(self):
        actions = {
            'iati_file_create': iati_actions.iati_file_create,
            'iati_file_update': iati_actions.iati_file_update,
            'iati_file_delete': iati_actions.iati_file_delete,
            'iati_file_show': iati_actions.iati_file_show,
            'iati_file_list': iati_actions.iati_file_list,
            'iati_resources_list': iati_actions.iati_resources_list,
            'generate_organization_xml': iati_actions.generate_organization_xml,
            'iati_generate': iati_actions.iati_generate,
            # Override CKAN core actions
            'resource_create': resources_actions.resource_create,
            'resource_update': resources_actions.resource_update,
        }

        return actions

    def get_auth_functions(self):
        return {
            'iati_file_create': iati_auth.iati_file_create,
            'iati_file_update': iati_auth.iati_file_update,
            'iati_file_delete': iati_auth.iati_file_delete,
            'iati_file_show': iati_auth.iati_file_show,
            'iati_file_list': iati_auth.iati_file_list,
            'iati_resources_list': iati_auth.iati_file_list,
            'generate_organization_xml': iati_auth.generate_organization_xml,
            'iati_generate': iati_auth.iati_generate,
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
            "iati_file_type": h.iati_file_types,
            "iati_namespaces": h.iati_namespaces,
            "check_mandatory_components": h.check_mandatory_components,
            "namespace_ready_for_generation": h.namespace_ready_for_generation,
        }
