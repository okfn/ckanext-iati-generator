import pytest
from ckan.lib.helpers import url_for
from ckan.tests import factories


class TestIatiTab:

    def test_iati_page_requires_sysadmin_no_user(self, app):
        """
        No user set it should return 403
        """
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])

        url = url_for("iati_generator.iati_page", package_id=dataset["id"])
        response = app.get(url, status=403)
        assert "Forbidden" in response.body

    def test_iati_page_requires_sysadmin_non_admin(self, app):
        """
        Non sysadmin user should return 403
        """
        user = factories.UserWithToken()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])

        url = url_for("iati_generator.iati_page", package_id=dataset["id"])

        auth = {"Authorization": user["token"]}
        response = app.get(url, headers=auth, status=403)
        assert "Sysadmin user required" in response.body

    def test_iati_page_allows_sysadmin(self, app):
        """
        sysadmin can access the page
        """
        user = factories.SysadminWithToken()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])

        url = url_for("iati_generator.iati_page", package_id=dataset["id"])
        auth = {"Authorization": user["token"]}
        response = app.get(url, headers=auth)

        assert response.status_code == 200
        assert "Generate test IATI" in response.body

    @pytest.mark.ckan_config("ckan.plugins", "iati_generator")
    def test_generate_iati_failure_no_crash(self, app):
        """
        Ensure generate_test_iati handles failure gracefully (no xml_string returned).
        """
        user = factories.SysadminWithToken()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        # Create a resource without required columns to force an error
        resource = factories.Resource(
            package_id=dataset["id"],
            format="CSV",
            url_type="upload",
            upload="invalid.csv",
        )

        url = url_for("iati_generator.generate_test_iati", package_id=dataset["id"])
        data = {"resource_id": resource["id"]}
        auth = {"Authorization": user["token"]}

        response = app.post(url, headers=auth, params=data, status=200)
        assert "Could not generate the XML file" in response.body

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
