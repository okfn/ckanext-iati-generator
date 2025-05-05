
import logging
from ckan import plugins as p
from ckan.plugins import toolkit

log = logging.getLogger(__name__)


class IatiGeneratorPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "ckanext-iati-generator")
