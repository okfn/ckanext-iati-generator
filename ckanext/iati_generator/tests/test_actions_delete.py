import pytest
from types import SimpleNamespace
from ckan.tests import factories
from ckan import model

from ckanext.iati_generator.models.iati_files import IATIFile
from ckanext.iati_generator.models.enums import IATIFileTypes


@pytest.fixture
def setup_data():
    """Base setup with users, organization, dataset and resource, with headers ready."""
    obj = SimpleNamespace()

    # Users + tokens
    obj.sysadmin = factories.SysadminWithToken()
    obj.sysadmin["headers"] = {"Authorization": obj.sysadmin["token"]}
    obj.user_admin = factories.UserWithToken()
    obj.user_admin["headers"] = {"Authorization": obj.user_admin["token"]}
    obj.user_editor = factories.UserWithToken()
    obj.user_editor["headers"] = {"Authorization": obj.user_editor["token"]}
    obj.user_member = factories.UserWithToken()
    obj.user_member["headers"] = {"Authorization": obj.user_member["token"]}

    # Organization + roles
    obj.org = factories.Organization(
        users=[
            {"name": obj.user_admin["name"], "capacity": "admin"},
            {"name": obj.user_editor["name"], "capacity": "editor"},
            {"name": obj.user_member["name"], "capacity": "member"},
        ]
    )

    # Dataset + resource
    obj.pkg = factories.Dataset(owner_org=obj.org["id"])
    obj.res = factories.Resource(
        package_id=obj.pkg["id"], format="CSV", url_type="upload",
        url="file.csv", name="file.csv",
    )

    return obj


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestIatiFileDeleteAction:
    """Test suite for iati_file_delete action: permissions, errors and correct execution."""

    def _api(self, action):  # helper
        return f"/api/3/action/{action}"

    def _create_file(self, app, headers, res_id, file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE.name):
        """Creates an IATIFile via API and returns the result dict."""
        return app.post(
            self._api("iati_file_create"),
            params={"resource_id": res_id, "file_type": file_type},
            headers=headers,
            status=200,
        ).json["result"]

    # --- PERMISSIONS / OK FLOWS ------------------------------------------------

    def test_delete_allowed_for_sysadmin(self, app, setup_data):
        created = self._create_file(app, setup_data.sysadmin["headers"], setup_data.res["id"])

        # sysadmin can delete
        resp = app.post(
            self._api("iati_file_delete"),
            params={"id": created["id"]},
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]
        assert resp["success"] is True

        # Confirm removed from DB
        assert model.Session.query(IATIFile).get(created["id"]) is None

    def test_delete_allowed_for_org_admin(self, app, setup_data):
        # Create file (sysadmin) and delete as organization admin
        created = self._create_file(app, setup_data.sysadmin["headers"], setup_data.res["id"])

        resp = app.post(
            self._api("iati_file_delete"),
            params={"id": created["id"]},
            headers=setup_data.user_admin["headers"],
            status=200,
        ).json["result"]
        assert resp["success"] is True
        assert model.Session.query(IATIFile).get(created["id"]) is None

    # --- PERMISSIONS / DENIED --------------------------------------------------

    def test_delete_denied_for_editor_and_member(self, app, setup_data):
        created = self._create_file(app, setup_data.sysadmin["headers"], setup_data.res["id"])

        # editor -> 403
        app.post(
            self._api("iati_file_delete"),
            params={"id": created["id"]},
            headers=setup_data.user_editor["headers"],
            status=403,
        )

        # member -> 403
        app.post(
            self._api("iati_file_delete"),
            params={"id": created["id"]},
            headers=setup_data.user_member["headers"],
            status=403,
        )

        # Still exists
        assert model.Session.query(IATIFile).get(created["id"]) is not None

    def test_delete_denied_when_admin_of_other_org(self, app, setup_data):
        # Create file in a different org
        other_org = factories.Organization()
        other_pkg = factories.Dataset(owner_org=other_org["id"])
        other_res = factories.Resource(
            package_id=other_pkg["id"], format="CSV", url_type="upload",
            url="other.csv", name="other.csv",
        )
        created = self._create_file(app, setup_data.sysadmin["headers"], other_res["id"])

        # Admin of original org cannot delete file from another org
        app.post(
            self._api("iati_file_delete"),
            params={"id": created["id"]},
            headers=setup_data.user_admin["headers"],
            status=403,
        )
        assert model.Session.query(IATIFile).get(created["id"]) is not None

    # --- ERRORS / MESSAGES -----------------------------------------------------

    def test_delete_missing_id_is_forbidden(self, app, setup_data):
        """If id is missing => 403 (no way to resolve permissions properly)."""
        app.post(
            self._api("iati_file_delete"),
            params={},  # missing id
            headers=setup_data.user_admin["headers"],
            status=403,
        )

    def test_delete_not_found_message(self, app, setup_data):
        """If the id doesn't exist => 404 + 'IATIFile <id> not found' message."""
        non_existent_id = 987654

        res = app.post(
            self._api("iati_file_delete"),
            params={"id": non_existent_id},
            headers=setup_data.sysadmin["headers"],
            status=404,  # ObjectNotFound -> 404
        )
        data = res.json
        # Robust check (payload format can vary)
        assert "not found" in str(data.get("error", "")).lower()
        assert str(non_existent_id) in str(data.get("error", ""))
