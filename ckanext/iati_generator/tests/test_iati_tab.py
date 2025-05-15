from ckan.lib.helpers import url_for
from ckan.tests import factories


class TestIatiTab:

    def test_iati_page_requires_sysadmin_no_user(self, app):
        """
        No REMOTE_USER set → debe devolver 403
        """
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])

        url = url_for("iati_generator.iati_page", package_id=dataset["id"])
        response = app.get(url, expect_errors=True)

        assert response.status_code == 403
        assert b"Forbidden" in response.body

    def test_iati_page_requires_sysadmin_non_admin(self, app):
        """
        Usuario logueado que NO es sysadmin → debe devolver 403
        """
        user = factories.UserWithToken()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])

        url = url_for("iati_generator.iati_page", package_id=dataset["id"])

        app.set_environ_base(REMOTE_USER=user["name"])
        auth = {"Authorization": user["token"]}
        response = app.get(url, headers=auth, expect_errors=True)

        assert response.status_code == 403
        assert b"Sysadmin user required" in response.body

    def test_iati_page_allows_sysadmin(self, app):
        """
        Usuario sysadmin → puede acceder
        """
        user = factories.SysadminWithToken()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])

        url = url_for("iati_generator.iati_page", package_id=dataset["id"])

        app.set_environ_base(REMOTE_USER=user["name"])
        auth = {"Authorization": user["token"]}
        response = app.get(url, headers=auth)

        assert response.status_code == 200
        assert b"pkg_dict" not in response.body
