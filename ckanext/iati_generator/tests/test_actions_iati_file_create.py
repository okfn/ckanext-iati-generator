import pytest
from ckan.tests import factories
from ckan import model
from ckanext.iati_generator.models.iati_files import IATIFile, DEFAULT_NAMESPACE
from ckanext.iati_generator.models.enums import IATIFileTypes


@pytest.fixture
def setup_data():
    org_admin = factories.UserWithToken()
    sysadmin = factories.SysadminWithToken()
    editor = factories.UserWithToken()
    member = factories.UserWithToken()

    org = factories.Organization(users=[
        {"name": org_admin["name"], "capacity": "admin"},
        {"name": editor["name"], "capacity": "editor"},
        {"name": member["name"], "capacity": "member"},
    ])

    pkg = factories.Dataset(owner_org=org["id"])
    res = factories.Resource(
        package_id=pkg["id"], format="CSV", url_type="upload",
        url="file.csv", name="file.csv",
    )

    # headers listos
    sysadmin["headers"] = {"Authorization": sysadmin["token"]}
    org_admin["headers"] = {"Authorization": org_admin["token"]}
    editor["headers"] = {"Authorization": editor["token"]}
    member["headers"] = {"Authorization": member["token"]}

    return {
        "sysadmin": sysadmin, "org_admin": org_admin,
        "editor": editor, "member": member,
        "pkg": pkg, "res": res,
    }


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestIatiFileCreateAction:

    def _api(self, action): return f"/api/3/action/{action}"

    def test_create_persists_row_and_defaults(self, app, setup_data):
        resp = app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": setup_data["res"]["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
            },
            headers=setup_data["sysadmin"]["headers"],
            status=200,
        ).json["result"]

        # Verificamos en DB
        obj = model.Session.query(IATIFile).get(resp["id"])
        assert obj is not None
        assert obj.resource_id == setup_data["res"]["id"]
        assert obj.file_type == IATIFileTypes.ORGANIZATION_MAIN_FILE.value
        assert obj.namespace == DEFAULT_NAMESPACE  # por defecto

    def test_create_accepts_enum_name_and_int(self, app, setup_data):
        # por nombre
        app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": setup_data["res"]["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
            },
            headers=setup_data["sysadmin"]["headers"],
            status=200,
        )
        # por int -> usar OTRO resource para evitar duplicado/constraint
        res2 = factories.Resource(
            package_id=setup_data["pkg"]["id"], format="CSV", url_type="upload",
            url="file2.csv", name="file2.csv",
        )
        app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": res2["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.value,
            },
            headers=setup_data["sysadmin"]["headers"],
            status=200,
        )

    def test_create_namespace_override(self, app, setup_data):
        resp = app.post(
            self._api("iati_file_create"),
            params={
                "resource_id": setup_data["res"]["id"],
                "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
                "namespace": "custom-ns",
            },
            headers=setup_data["sysadmin"]["headers"],
            status=200,
        ).json["result"]
        assert resp["namespace"] == "custom-ns"

    def test_create_validation_error_missing_resource_id(self, app, setup_data):
        # con sysadmin pasa el auth, debe fallar validación (CKAN => 409)
        app.post(
            self._api("iati_file_create"),
            params={"file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name},
            headers=setup_data["sysadmin"]["headers"],
            status=409,
        )

    def test_permission_matrix(self, app, setup_data):
        payload = {
            "resource_id": setup_data["res"]["id"],
            "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
        }
        # sysadmin OK
        app.post(self._api("iati_file_create"), params=payload,
                 headers=setup_data["sysadmin"]["headers"], status=200)
        # admin org OK -> usar OTRO resource para evitar constraint
        res_admin = factories.Resource(
            package_id=setup_data["pkg"]["id"], format="CSV", url_type="upload",
            url="file_admin.csv", name="file_admin.csv",
        )
        payload_admin = {
            "resource_id": res_admin["id"],
            "file_type": IATIFileTypes.ORGANIZATION_NAMES_FILE.name,
        }
        app.post(self._api("iati_file_create"), params=payload_admin,
                 headers=setup_data["org_admin"]["headers"], status=200)
        # editor 403
        app.post(self._api("iati_file_create"),
                 params={"resource_id": setup_data["res"]["id"],
                         "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name},
                 headers=setup_data["editor"]["headers"], status=403)
        # member 403
        app.post(self._api("iati_file_create"),
                 params={"resource_id": setup_data["res"]["id"],
                         "file_type": IATIFileTypes.ORGANIZATION_NAMES_FILE.name},
                 headers=setup_data["member"]["headers"], status=403)
