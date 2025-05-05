import pytest
from ckan import plugins


@pytest.mark.ckan_config("ckan.plugins", "iati_generator")
@pytest.mark.usefixtures("with_plugins")
def test_plugin():
    assert plugins.plugin_loaded("iati_generator")
