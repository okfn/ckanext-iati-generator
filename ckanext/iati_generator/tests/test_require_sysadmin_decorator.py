from ckan.lib.helpers import url_for
from ckan.tests import factories


class TestSysadminDecorator:

    def test_require_sysadmin_user_decorator_no_user(self, app):
        """
        Test that the require_sysadmin_user decorator denies access
        when no user is logged in.
        """
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        url = url_for('iati_generator.iati_page', package_id=dataset['id'])
        response = app.get(url, expect_errors=True)
        assert response.status_code == 403

    def test_require_sysadmin_user_decorator_non_admin(self, app):
        """
        Test that the require_sysadmin_user decorator denies access
        when a non-admin user is logged in.
        """
        user = factories.UserWithToken()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        url = url_for('iati_generator.iati_page', package_id=dataset['id'])
        auth = {"Authorization": user['token']}
        response = app.get(url, headers=auth, expect_errors=True)
        assert response.status_code == 403

    def test_require_sysadmin_user_decorator_admin(self, app):
        """
        Test that the require_sysadmin_user decorator allows access
        when a sysadmin user is logged in.
        """
        user_sysadmin = factories.SysadminWithToken()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        url = url_for('iati_generator.iati_page', package_id=dataset['id'])
        auth = {"Authorization": user_sysadmin['token']}
        response = app.get(url, headers=auth)
        assert response.status_code == 200
