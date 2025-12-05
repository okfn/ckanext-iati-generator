from ckan.tests import factories
from ckanext.iati_generator.helpers import iati_tab_enabled
from ckan.plugins import toolkit


class TestIatiTab:

    def test_serve_iati_file_not_found(self, app):
        """
        Test that serve_iati_file returns 404 if file is missing.
        """
        user = factories.SysadminWithToken()
        resource_id = "abc123456789"
        fake_filename = "missing_file.xml"
        url = f"/iati-dataset/static-iati/{resource_id}/{fake_filename}"
        auth = {"Authorization": user["token"]}
        response = app.get(url, headers=auth, status=404)
        assert "XML file not found" in response.body

    @pytest.mark.ckan_config("ckanext.iati_generator.hide_tab", "true")
    def test_iati_tab_enabled_false_when_config_true(self):
        """
        Test that iati_tab_enabled returns False when the config option is set to 'true'.

        This simulates the case where the administrator has explicitly disabled
        the IATI tab using the config option `ckanext.iati_generator.hide_tab = true`.
        """
        assert iati_tab_enabled() is False

    @pytest.mark.ckan_config("ckanext.iati_generator.hide_tab", "false")
    def test_iati_tab_enabled_true_when_config_false(self):
        """
        Test that iati_tab_enabled returns True when the config option is set to 'false'.

        This is the default behavior where the IATI tab is enabled unless explicitly disabled.
        """
        assert iati_tab_enabled() is True

    def test_iati_tab_enabled_default_true(self, monkeypatch):
        """
        Test that iati_tab_enabled returns True when the config option is not set.

        Ensures the helper falls back to the expected default (enabled) behavior if
        the `ckanext.iati_generator.hide_tab` config is not defined at all.
        """
        if "ckanext.iati_generator.hide_tab" in toolkit.config:
            monkeypatch.delitem(toolkit.config, "ckanext.iati_generator.hide_tab", None)
        assert iati_tab_enabled() is True
