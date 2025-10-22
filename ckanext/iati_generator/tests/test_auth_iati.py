import pytest
from ckan.tests import factories

from ckanext.iati_generator.models.enums import IATIFileTypes


@pytest.mark.usefixtures('with_plugins', 'clean_db')
class TestIatiAuth:
    def _make_dataset_with_resource_and_members(self):
        # Users
        user_admin = factories.UserWithToken()
        user_editor = factories.UserWithToken()
        user_member = factories.UserWithToken()

        # Organization with members defined in the factory
        org = factories.Organization(
            users=[
                {"name": user_admin["name"], "capacity": "admin"},
                {"name": user_editor["name"], "capacity": "editor"},
                {"name": user_member["name"], "capacity": "member"},
            ]
        )

        pkg = factories.Dataset(owner_org=org["id"])
        res = factories.Resource(
            package_id=pkg["id"],
            format="CSV",
            url_type="upload",
            url="test.csv",
            name="test.csv",
        )
        users = {
            "admin": user_admin,
            "editor": user_editor,
            "member": user_member,
        }
        return org, pkg, res, users

    def _api(self, action):
        return f"/api/3/action/{action}"

    def test_create_denied_for_regular_member(self, app):
        """A 'member' user of the org cannot create an IATIFile."""
        org, pkg, res, users = self._make_dataset_with_resource_and_members()
        payload = {
            "resource_id": res["id"],
            "package_id": pkg["id"],
            "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
        }
        headers = {"Authorization": users["member"]["token"]}
        app.post(self._api("iati_file_create"), params=payload, headers=headers, status=403)

    def test_create_allowed_for_sysadmin(self, app):
        """A sysadmin can create an IATIFile."""
        sys = factories.SysadminWithToken()
        org, pkg, res, _ = self._make_dataset_with_resource_and_members()
        payload = {
            "resource_id": res["id"],
            "package_id": pkg["id"],
            "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
        }
        headers = {"Authorization": sys["token"]}
        resp = app.post(self._api("iati_file_create"), params=payload, headers=headers, status=200)
        assert resp.json["success"] is True
        assert "id" in resp.json["result"]

    def test_create_allowed_for_org_admin(self, app):
        """The admin of the organization owning the dataset can create an IATIFile."""
        org, pkg, res, users = self._make_dataset_with_resource_and_members()
        payload = {
            "resource_id": res["id"],
            "package_id": pkg["id"],
            "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
        }
        headers = {"Authorization": users["admin"]["token"]}
        resp = app.post(self._api("iati_file_create"), params=payload, headers=headers, status=200)
        assert resp.json["success"] is True
        assert "id" in resp.json["result"]

    def test_update_allowed_resolving_by_iati_id_for_org_admin(self, app):
        """The admin of the org can update an IATIFile (resolved by ID)."""
        # Create as sysadmin
        sys = factories.SysadminWithToken()
        org, pkg, res, users = self._make_dataset_with_resource_and_members()
        created = app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": res["id"],
                "package_id": pkg["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
            },
            headers={"Authorization": sys["token"]},
            status=200,
        ).json["result"]

        # Update as org admin
        headers = {"Authorization": users["admin"]["token"]}
        resp = app.post(
            self._api("iati_file_update"),
            params={"id": created["id"], "package_id": pkg["id"], "namespace": "updated-ns"},
            headers=headers,
            status=200,
        )
        assert resp.json["success"] is True
        assert resp.json["result"]["namespace"] == "updated-ns"

    def test_delete_denied_for_regular_member(self, app):
        """A 'member' user cannot delete an IATIFile."""
        sys = factories.SysadminWithToken()
        org, pkg, res, users = self._make_dataset_with_resource_and_members()
        created = app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": res["id"],
                "package_id": pkg["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
            },
            headers={"Authorization": sys["token"]},
            status=200,
        ).json["result"]

        headers = {"Authorization": users["member"]["token"]}
        app.post(
            self._api("iati_file_delete"),
            params={"id": created["id"], "package_id": pkg["id"]},
            headers=headers,
            status=403,
        )

    def test_show_is_open_for_anonymous(self, app):
        """Anyone can view an IATIFile by ID (without Authorization)."""
        sys = factories.SysadminWithToken()
        org, pkg, res, _ = self._make_dataset_with_resource_and_members()
        created = app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": res["id"],
                "package_id": pkg["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
            },
            headers={"Authorization": sys["token"]},
            status=200,
        ).json["result"]

        resp = app.post(self._api("iati_file_show"), params={"id": created["id"]}, status=200)
        assert resp.json["success"] is True
        assert resp.json["result"]["id"] == created["id"]
