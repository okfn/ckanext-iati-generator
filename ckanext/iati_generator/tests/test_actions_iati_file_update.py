import pytest
from types import SimpleNamespace
from ckan.tests import factories
from ckan import model

from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.models.iati_files import IATIFile
from ckanext.iati_generator.tests.factories import create_iati_file


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
class TestIatiFileUpdateAction:
    """Test suite for iati_file_update action: permissions and correct execution."""

    def _api(self, action):  # helper
        return f"/api/3/action/{action}"

    # --- PERMISSIONS ----------------------------------------------------------

    def test_update_allowed_for_sysadmin_and_org_admin(self, app, setup_data):
        """Test that sysadmin and organization admin users can update IATI files."""
        created = create_iati_file(resource_id=setup_data.res["id"])

        # sysadmin can update
        resp = app.post(
            self._api("iati_file_update"),
            params={"id": created.id, "namespace": "ns-sys"},
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]
        assert resp["namespace"] == "ns-sys"

        # organization owner admin can update
        resp2 = app.post(
            self._api("iati_file_update"),
            params={"id": created.id, "namespace": "ns-admin"},
            headers=setup_data.user_admin["headers"],
            status=200,
        ).json["result"]
        assert resp2["namespace"] == "ns-admin"

    def test_update_denied_for_editor_and_member(self, app, setup_data):
        """Test that editor and member users are denied access to update IATI files."""
        created = create_iati_file(resource_id=setup_data.res["id"])

        # editor -> 403
        app.post(
            self._api("iati_file_update"),
            params={"id": created.id, "namespace": "x"},
            headers=setup_data.user_editor["headers"],
            status=403,
        )

        # member -> 403
        app.post(
            self._api("iati_file_update"),
            params={"id": created.id, "namespace": "y"},
            headers=setup_data.user_member["headers"],
            status=403,
        )

    def test_update_denied_when_admin_of_other_org(self, app, setup_data):
        """Test that admin users cannot update files belonging to other organizations."""
        other_org = factories.Organization()
        other_pkg = factories.Dataset(owner_org=other_org["id"])
        other_res = factories.Resource(
            package_id=other_pkg["id"], format="CSV", url_type="upload",
            url="other.csv", name="other.csv",
        )

        created = create_iati_file(resource_id=other_res["id"])

        app.post(
            self._api("iati_file_update"),
            params={"id": created.id, "namespace": "nope"},
            headers=setup_data.user_admin["headers"],
            status=403,
        )

    def test_update_fails_without_id_and_resource_id(self, app, setup_data):
        """Test that update fails without id or resource_id to resolve the dataset."""
        app.post(
            self._api("iati_file_update"),
            params={"namespace": "x"},  # missing id and resource_id
            headers=setup_data.user_admin["headers"],
            status=403,
        )

    # --- EXECUTION / FIELDS ---------------------------------------------------

    def test_update_accepts_file_type_by_name_and_int(self, app, setup_data):
        """Test that file_type can be updated using both enum name and integer value."""
        created = create_iati_file(resource_id=setup_data.res["id"])

        # Change by name
        resp = app.post(
            self._api("iati_file_update"),
            params={"id": created.id, "file_type": IATIFileTypes.ORGANIZATION_NAMES_FILE.name},
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]
        assert resp["file_type"] == IATIFileTypes.ORGANIZATION_NAMES_FILE.name

        # Change by int (enum value)
        resp2 = app.post(
            self._api("iati_file_update"),
            params={"id": created.id, "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.value},
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]
        assert resp2["file_type"] == IATIFileTypes.ORGANIZATION_MAIN_FILE.name

    def test_update_toggle_is_valid_and_last_error(self, app, setup_data):
        """Test that is_valid flag and last_error field can be updated and toggled correctly."""
        created = create_iati_file(resource_id=setup_data.res["id"])

        # Mark as invalid with error
        resp = app.post(
            self._api("iati_file_update"),
            params={"id": created.id, "is_valid": False, "last_error": "boom"},
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]
        assert resp["is_valid"] is False
        assert resp["last_error"] == "boom"

        # Mark as valid and clear error
        resp2 = app.post(
            self._api("iati_file_update"),
            params={"id": created.id, "is_valid": True, "last_error": None},
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]
        assert resp2["is_valid"] is True
        assert resp2["last_error"] is None

        # Confirm in DB
        obj = model.Session.query(IATIFile).get(created.id)
        assert obj.is_valid is True
        assert obj.last_error is None

    # --- ERRORS / MESSAGES ---------------------------------------------------

    def test_update_invalid_boolean_message(self, app, setup_data):
        """If is_valid is not a valid boolean => 409 + 'Invalid boolean' message."""
        created = create_iati_file(resource_id=setup_data.res["id"])

        res = app.post(
            self._api("iati_file_update"),
            params={"id": created.id, "is_valid": "maybe"},
            headers=setup_data.sysadmin["headers"],
            status=409,  # ValidationError -> 409
        )
        data = res.json
        assert data["success"] is False
        # CKAN may wrap in list; we check by substring
        assert "Invalid boolean" in str(data.get("error", ""))

    def test_update_invalid_file_type_name_message(self, app, setup_data):
        """If file_type is an invalid enum name => 409 + 'Invalid IATIFileTypes value' message."""
        created = create_iati_file(resource_id=setup_data.res["id"])

        res = app.post(
            self._api("iati_file_update"),
            params={"id": created.id, "file_type": "NOT_A_REAL_TYPE"},
            headers=setup_data.sysadmin["headers"],
            status=409,
        )
        data = res.json
        assert data["success"] is False
        assert "Invalid IATIFileTypes value" in str(data.get("error", ""))

    def test_update_invalid_file_type_int_message(self, app, setup_data):
        """If file_type is a non-existent integer => 409 + 'Invalid IATIFileTypes value' message."""
        created = create_iati_file(resource_id=setup_data.res["id"])

        res = app.post(
            self._api("iati_file_update"),
            params={"id": created.id, "file_type": 999},
            headers=setup_data.sysadmin["headers"],
            status=409,
        )
        data = res.json
        assert data["success"] is False
        assert "Invalid IATIFileTypes value" in str(data.get("error", ""))

    def test_update_not_found_message(self, app, setup_data):
        """If the id doesn't exist => 404 + 'IATIFile <id> not found' message."""
        non_existent_id = 999999

        res = app.post(
            self._api("iati_file_update"),
            params={"id": non_existent_id, "namespace": "x"},
            headers=setup_data.sysadmin["headers"],
            status=404,  # ObjectNotFound -> 404
        )
        data = res.json
        # CKAN error payload may vary, we use robust substring check
        assert "not found" in str(data.get("error", "")).lower()
        assert str(non_existent_id) in str(data.get("error", ""))
