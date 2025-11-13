import pytest
from types import SimpleNamespace

from ckan.tests import factories
from ckan import model
from ckanext.iati_generator.models.iati_files import IATIFile, DEFAULT_NAMESPACE
from ckanext.iati_generator.models.enums import IATIFileTypes


@pytest.fixture
def setup_data():
    """Create users, org, dataset and base resource — with tokens+headers ready."""
    obj = SimpleNamespace()

    # Users + tokens
    obj.org_admin = factories.UserWithToken()
    obj.org_admin["headers"] = {"Authorization": obj.org_admin["token"]}

    obj.sysadmin = factories.SysadminWithToken()
    obj.sysadmin["headers"] = {"Authorization": obj.sysadmin["token"]}

    obj.editor = factories.UserWithToken()
    obj.editor["headers"] = {"Authorization": obj.editor["token"]}

    obj.member = factories.UserWithToken()
    obj.member["headers"] = {"Authorization": obj.member["token"]}

    # Org with roles
    obj.org = factories.Organization(
        users=[
            {"name": obj.org_admin["name"], "capacity": "admin"},
            {"name": obj.editor["name"], "capacity": "editor"},
            {"name": obj.member["name"], "capacity": "member"},
        ]
    )

    # Dataset + base resource
    obj.pkg = factories.Dataset(owner_org=obj.org["id"])
    obj.res = factories.Resource(
        package_id=obj.pkg["id"],
        format="CSV",
        url_type="upload",
        url="file.csv",
        name="file.csv",
    )

    return obj


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestIatiFileCreateAction:

    def _api(self, action):
        return f"/api/3/action/{action}"

    def test_create_persists_row_and_defaults(self, app, setup_data):
        """test successful creation persists row with default values"""
        resp = app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": setup_data.res["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
            },
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]

        # Verify in DB
        obj = model.Session.query(IATIFile).get(resp["id"])
        assert obj is not None
        assert obj.resource_id == setup_data.res["id"]
        assert obj.file_type == IATIFileTypes.ORGANIZATION_MAIN_FILE.value
        assert obj.namespace == DEFAULT_NAMESPACE  # default value

    def test_create_accepts_enum_name_and_int(self, app, setup_data):
        """test file_type can be provided as enum name or int value"""
        # by name
        app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": setup_data.res["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
            },
            headers=setup_data.sysadmin["headers"],
            status=200,
        )
        # by int -> use ANOTHER resource to avoid duplicate/constraint
        res2 = factories.Resource(
            package_id=setup_data.pkg["id"],
            format="CSV",
            url_type="upload",
            url="file2.csv",
            name="file2.csv",
        )
        app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": res2["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.value,
            },
            headers=setup_data.sysadmin["headers"],
            status=200,
        )

    def test_create_namespace_override(self, app, setup_data):
        """test namespace can be overridden"""
        resp = app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": setup_data.res["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
                "namespace": "custom-ns",
            },
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]
        assert resp["namespace"] == "custom-ns"

    def test_create_validation_error_missing_resource_id(self, app, setup_data):
        """test missing resource_id raises validation error"""
        app.post(
            self._api("iati_file_create"),
            params={"file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name},
            headers=setup_data.sysadmin["headers"],
            status=409,
        )

    def test_permission_matrix(self, app, setup_data):
        """Test permission matrix for IATI file creation."""
        payload = {
            "resource_id": setup_data.res["id"],
            "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
        }
        # sysadmin OK
        app.post(
            self._api("iati_file_create"),
            params=payload,
            headers=setup_data.sysadmin["headers"],
            status=200,
        )

        # org admin OK -> use ANOTHER resource to avoid constraint
        res_admin = factories.Resource(
            package_id=setup_data.pkg["id"],
            format="CSV",
            url_type="upload",
            url="file_admin.csv",
            name="file_admin.csv",
        )
        payload_admin = {
            "resource_id": res_admin["id"],
            "file_type": IATIFileTypes.ORGANIZATION_NAMES_FILE.name,
        }
        app.post(
            self._api("iati_file_create"),
            params=payload_admin,
            headers=setup_data.org_admin["headers"],
            status=200,
        )

        # editor 403
        app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": setup_data.res["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
            },
            headers=setup_data.editor["headers"],
            status=403,
        )

        # member 403
        app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": setup_data.res["id"],
                "file_type": IATIFileTypes.ORGANIZATION_NAMES_FILE.name,
            },
            headers=setup_data.member["headers"],
            status=403,
        )
