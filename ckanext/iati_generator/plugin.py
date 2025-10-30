
import logging
from ckan import plugins as p
from ckan.plugins import toolkit
from ckanext.iati_generator.actions.iati import (generate_iati_xml, iati_file_create,
                                                 iati_file_update, iati_file_delete,
                                                 iati_file_show)
from ckanext.iati_generator.auth import iati as iati_auth
from ckan.lib.plugins import DefaultTranslation
from ckanext.iati_generator.blueprint.iati import iati_blueprint
from ckanext.iati_generator.blueprint.admin import iati_blueprint_admin, iati_file_admin
from ckanext.iati_generator import helpers as h


log = logging.getLogger(__name__)


class IatiGeneratorPlugin(p.SingletonPlugin, DefaultTranslation):
    p.implements(p.IConfigurer)
    p.implements(p.IBlueprint)
    p.implements(p.IActions)
    p.implements(p.ITranslation)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IAuthFunctions)
    p.implements(p.IValidators)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "iati_generator")

    def get_blueprint(self):
        return [
            iati_blueprint,
            iati_blueprint_admin,
            iati_file_admin,
        ]

    def get_actions(self):
        return {
            "generate_iati_xml": generate_iati_xml,
            'iati_file_create': iati_file_create,
            'iati_file_update': iati_file_update,
            'iati_file_delete': iati_file_delete,
            'iati_file_show': iati_file_show,
        }

    def get_auth_functions(self):
        return {
            'iati_file_create': iati_auth.iati_file_create,
            'iati_file_update': iati_auth.iati_file_update,
            'iati_file_delete': iati_auth.iati_file_delete,
            'iati_file_show': iati_auth.iati_file_show,
        }

    def get_validators(self):
        return {
            "iati_protect_org_admin_only": iati_auth.iati_protect_org_admin_only
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
            "iati_tab_enabled": h.iati_tab_enabled,
            "iati_file_type": h.iati_file_type,
        }
