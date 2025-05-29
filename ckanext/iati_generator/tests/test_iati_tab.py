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
