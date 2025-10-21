import pytest
from ckan.tests import factories

from ckanext.iati_generator.models.enums import IATIFileTypes


@pytest.mark.ckan_config("ckan.plugins", "iati_generator")
class TestIatiAuth:
    def _make_dataset_with_resource(self):
        org = factories.Organization()
        pkg = factories.Dataset(owner_org=org["id"])
        res = factories.Resource(
            package_id=pkg["id"],
            format="CSV",
            url_type="upload",
            url="test.csv",
            name="test.csv",
        )
        return org, pkg, res

    def _api(self, action):
        return f"/api/3/action/{action}"

    def _make_org_admin(self, app, org_id, user_id):
        """Turn user_id into an organization admin using the API (requires sysadmin token)."""
        sys = factories.SysadminWithToken()
        headers = {"Authorization": sys["token"]}
        params = {
            "id": org_id,
            "object": user_id,
            "object_type": "user",
            "capacity": "admin",
        }
        # status=200 even if it already exists returns OK/Conflict managed by CKAN;
        # for tests it's enough that it doesn't raise.
        app.post(self._api("member_create"), headers=headers, params=params, status=200)

    def test_create_denied_for_regular_user(self, app):
        """A regular user cannot create an IATIFile."""
        user = factories.UserWithToken()
        org, pkg, res = self._make_dataset_with_resource()

        payload = {
            "resource_id": res["id"],
            "package_id": pkg["id"],
            "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,  # use enum name
        }
        headers = {"Authorization": user["token"]}
        app.post(self._api("iati_file_create"), params=payload, headers=headers, status=403)

    def test_create_allowed_for_sysadmin(self, app):
        """A sysadmin can create an IATIFile."""
        user = factories.SysadminWithToken()
        org, pkg, res = self._make_dataset_with_resource()

        payload = {
            "resource_id": res["id"],
            "package_id": pkg["id"],
            "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
        }
        headers = {"Authorization": user["token"]}
        resp = app.post(self._api("iati_file_create"), params=payload, headers=headers, status=200)
        assert resp.json["success"] is True
        assert "id" in resp.json["result"]

    def test_create_allowed_for_org_admin(self, app):
        """An admin of the org owning the dataset can create an IATIFile"""
        user = factories.UserWithToken()
        org, pkg, res = self._make_dataset_with_resource()
        self._make_org_admin(app, org["id"], user["id"])

        payload = {
            "resource_id": res["id"],
            "package_id": pkg["id"],
            "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
        }
        headers = {"Authorization": user["token"]}
        resp = app.post(self._api("iati_file_create"), params=payload, headers=headers, status=200)
        assert resp.json["success"] is True
        assert "id" in resp.json["result"]

    def test_update_allowed_resolving_by_iati_id_for_org_admin(self, app):
        """An admin of the org owning the dataset can update an IATIFile"""
        # Create IATIFile as sysadmin
        sys = factories.SysadminWithToken()
        org, pkg, res = self._make_dataset_with_resource()
        create_headers = {"Authorization": sys["token"]}
        created = app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": res["id"],
                "package_id": pkg["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
            },
            headers=create_headers,
            status=200,
        ).json["result"]

        # Make the user an org admin and update by IATIFile ID
        user = factories.UserWithToken()
        self._make_org_admin(app, org["id"], user["id"])
        upd_headers = {"Authorization": user["token"]}

        # Update a text field (avoids boolean casting issues in the action)
        resp = app.post(
            self._api("iati_file_update"),
            params={"id": created["id"], "package_id": pkg["id"], "namespace": "updated-ns"},
            headers=upd_headers,
            status=200,
        )
        assert resp.json["success"] is True
        assert resp.json["result"]["namespace"] == "updated-ns"

    def test_delete_denied_for_regular_user(self, app):
        """A regular user cannot delete an IATIFile."""
        sys = factories.SysadminWithToken()
        org, pkg, res = self._make_dataset_with_resource()
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

        user = factories.UserWithToken()
        headers = {"Authorization": user["token"]}
        app.post(
            self._api("iati_file_delete"),
            params={"id": created["id"], "package_id": pkg["id"]},
            headers=headers,
            status=403,
        )

    def test_show_is_open_for_anonymous(self, app):
        """Anyone can view an IATIFile if they know its ID."""
        sys = factories.SysadminWithToken()
        org, pkg, res = self._make_dataset_with_resource()
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

        # without Authorization → should allow show
        resp = app.post(self._api("iati_file_show"), params={"id": created["id"]}, status=200)
        assert resp.json["success"] is True
        assert resp.json["result"]["id"] == created["id"]
