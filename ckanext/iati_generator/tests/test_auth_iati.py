from types import SimpleNamespace
import pytest
from ckan.tests import factories
from ckanext.iati_generator.models.enums import IATIFileTypes


@pytest.fixture
def setup_data():
    """Create reusable data for IATIFile authorization tests."""
    obj = SimpleNamespace()

    # Users
    obj.sysadmin = factories.SysadminWithToken()
    obj.sysadmin["headers"] = {"Authorization": obj.sysadmin["token"]}
    obj.user_admin = factories.UserWithToken()
    obj.user_admin["headers"] = {"Authorization": obj.user_admin["token"]}
    obj.user_editor = factories.UserWithToken()
    obj.user_editor["headers"] = {"Authorization": obj.user_editor["token"]}
    obj.user_member = factories.UserWithToken()
    obj.user_member["headers"] = {"Authorization": obj.user_member["token"]}

    # Organization and dataset
    obj.org = factories.Organization(
        users=[
            {"name": obj.user_admin["name"], "capacity": "admin"},
            {"name": obj.user_editor["name"], "capacity": "editor"},
            {"name": obj.user_member["name"], "capacity": "member"},
        ]
    )

    obj.pkg = factories.Dataset(owner_org=obj.org["id"])
    obj.res = factories.Resource(
        package_id=obj.pkg["id"],
        format="CSV",
        url_type="upload",
        url="test.csv",
        name="test.csv",
    )

    return obj


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestIatiAuth:
    """Authorization tests for IATIFile actions."""

    def _api(self, action):
        return f"/api/3/action/{action}"

    # --- CREATE ---------------------------------------------------------------

    def test_create_denied_for_regular_member(self, app, setup_data):
        """A 'member' user of the org cannot create an IATIFile."""

        payload = {
            "resource_id": setup_data.res["id"],
            "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
        }
        app.post(
            self._api("iati_file_create"),
            params=payload,
            headers=setup_data.user_member["headers"],
            status=403,
        )

    def test_create_allowed_for_sysadmin(self, app, setup_data):
        """A sysadmin can create an IATIFile."""
        payload = {
            "resource_id": setup_data.res["id"],
            "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
        }
        resp = app.post(
            self._api("iati_file_create"),
            params=payload,
            headers=setup_data.sysadmin["headers"],
            status=200,
        )
        assert resp.json["success"] is True
        assert "id" in resp.json["result"]

    def test_create_allowed_for_org_admin(self, app, setup_data):
        """The admin of the organization owning the dataset can create an IATIFile."""
        payload = {
            "resource_id": setup_data.res["id"],
            "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
        }
        resp = app.post(
            self._api("iati_file_create"),
            params=payload,
            headers=setup_data.user_admin["headers"],
            status=200,
        )
        assert resp.json["success"] is True
        assert "id" in resp.json["result"]

    # --- UPDATE ---------------------------------------------------------------

    def test_update_allowed_resolving_by_iati_id_for_org_admin(self, app, setup_data):
        """The org admin can update the IATIFile created by sysadmin."""
        created = app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": setup_data.res["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
            },
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]

        resp = app.post(
            self._api("iati_file_update"),
            params={
                "id": created["id"],
                "namespace": "updated-ns",
            },
            headers=setup_data.user_admin["headers"],
            status=200,
        )
        assert resp.json["success"] is True
        assert resp.json["result"]["namespace"] == "updated-ns"

    # --- DELETE ---------------------------------------------------------------

    def test_delete_denied_for_regular_member(self, app, setup_data):
        """A 'member' user cannot delete an IATIFile."""
        created = app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": setup_data.res["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
            },
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]

        app.post(
            self._api("iati_file_delete"),
            params={"id": created["id"], "package_id": setup_data.pkg["id"]},
            headers=setup_data.user_member["headers"],
            status=403,
        )

    # --- SHOW -----------------------------------------------------------------

    def test_show_is_open_for_anonymous(self, app, setup_data):
        """Anyone can view an IATIFile by ID (without Authorization)."""
        created = app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": setup_data.res["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
            },
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]

        resp = app.post(self._api("iati_file_show"), params={"id": created["id"]}, status=200)
        assert resp.json["success"] is True
        assert resp.json["result"]["id"] == created["id"]
        assert resp.json["result"]["resource_id"] == created["resource_id"]
        assert resp.json["result"]["namespace"] == created["namespace"]
        assert resp.json["result"]["file_type"] == created["file_type"]
        assert resp.json["result"]["is_valid"] == created["is_valid"]
        assert resp.json["result"]["last_error"] == created["last_error"]

    # --- ERRORS / CLEAR MESSAGES -------------------------------------------

    def test_create_fails_without_resource_id(self, app, setup_data):
        """If resource_id is missing, authorization should reject with a clear message."""
        payload = {
            # resource_id intentionally absent
            "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
        }
        resp = app.post(
            self._api("iati_file_create"),
            params=payload,
            headers=setup_data.user_admin["headers"],
            status=403,
        )
        # CKAN returns {"success": False, "error": {"message": "...", "__type": "Authorization Error"}}
        assert "error" in resp.json
        assert "Missing or invalid resource_id" in resp.json["error"]["message"]

    def test_update_fails_without_id_and_resource_id(self, app, setup_data):
        """Without id or resource_id the dataset cannot be resolved (update)."""
        resp = app.post(
            self._api("iati_file_update"),
            params={"namespace": "x"},  # nothing provided to resolve package_id
            headers=setup_data.user_admin["headers"],
            status=403,
        )
        assert "Cannot resolve dataset for IATI file update" in resp.json["error"]["message"]

    def test_delete_fails_without_id_and_resource_id(self, app, setup_data):
        """Without id or resource_id the dataset cannot be resolved (delete)."""
        resp = app.post(
            self._api("iati_file_delete"),
            params={},  # empty on purpose
            headers=setup_data.user_admin["headers"],
            status=403,
        )
        assert "Cannot resolve dataset for IATI file deletion" in resp.json["error"]["message"]

    def test_create_denied_for_editor(self, app, setup_data):
        """An 'editor' cannot create (only org admin or sysadmin can)."""
        payload = {
            "resource_id": setup_data.res["id"],
            "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
        }
        app.post(
            self._api("iati_file_create"),
            params=payload,
            headers=setup_data.user_editor["headers"],
            status=403,
        )

    def test_update_denied_when_not_admin_of_owning_org(self, app, setup_data):
        """If the dataset belongs to another org, the admin of the original org cannot update."""
        # Create another organization + dataset + resource (where user_admin is NOT an admin)
        other_org = factories.Organization()
        other_pkg = factories.Dataset(owner_org=other_org["id"])
        other_res = factories.Resource(
            package_id=other_pkg["id"], format="CSV", url_type="upload", url="other.csv", name="other.csv"
        )

        # Create IATIFile in that dataset as sysadmin
        created = app.post(
            self._api("iati_file_create"),
            params={"resource_id": other_res["id"], "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name},
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]

        # Attempted update by original org admin -> 403
        app.post(
            self._api("iati_file_update"),
            params={"id": created["id"], "namespace": "should-not-allow"},
            headers=setup_data.user_admin["headers"],
            status=403,
        )
