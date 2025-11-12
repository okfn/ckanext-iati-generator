import pytest
from types import SimpleNamespace
from ckan.tests import factories
from ckan import model

from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.models.iati_files import IATIFile


@pytest.fixture
def setup_data():
    """Usuarios + org + dataset + resource base, con headers listos."""
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

    # Org + roles
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
    """Suite específica de iati_file_update: permisos y ejecución correcta."""

    def _api(self, action):  # helper
        return f"/api/3/action/{action}"

    def _create_file(self, app, headers, res_id, file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE.name):
        """Crea un IATIFile vía API y devuelve el dict result."""
        return app.post(
            self._api("iati_file_create"),
            params={"resource_id": res_id, "file_type": file_type},
            headers=headers,
            status=200,
        ).json["result"]

    # --- PERMISOS -------------------------------------------------------------

    def test_update_allowed_for_sysadmin_and_org_admin(self, app, setup_data):
        created = self._create_file(app, setup_data.sysadmin["headers"], setup_data.res["id"])

        # sysadmin puede actualizar
        resp = app.post(
            self._api("iati_file_update"),
            params={"id": created["id"], "namespace": "ns-sys"},
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]
        assert resp["namespace"] == "ns-sys"

        # admin de la org dueña puede actualizar
        resp2 = app.post(
            self._api("iati_file_update"),
            params={"id": created["id"], "namespace": "ns-admin"},
            headers=setup_data.user_admin["headers"],
            status=200,
        ).json["result"]
        assert resp2["namespace"] == "ns-admin"

    def test_update_denied_for_editor_and_member(self, app, setup_data):
        created = self._create_file(app, setup_data.sysadmin["headers"], setup_data.res["id"])

        # editor -> 403
        app.post(
            self._api("iati_file_update"),
            params={"id": created["id"], "namespace": "x"},
            headers=setup_data.user_editor["headers"],
            status=403,
        )

        # member -> 403
        app.post(
            self._api("iati_file_update"),
            params={"id": created["id"], "namespace": "y"},
            headers=setup_data.user_member["headers"],
            status=403,
        )

    def test_update_denied_when_admin_of_other_org(self, app, setup_data):
        """Si el archivo pertenece a otro dataset/organización, un admin ajeno no puede actualizar."""
        other_org = factories.Organization()
        other_pkg = factories.Dataset(owner_org=other_org["id"])
        other_res = factories.Resource(
            package_id=other_pkg["id"], format="CSV", url_type="upload",
            url="other.csv", name="other.csv",
        )

        created = self._create_file(app, setup_data.sysadmin["headers"], other_res["id"])

        app.post(
            self._api("iati_file_update"),
            params={"id": created["id"], "namespace": "nope"},
            headers=setup_data.user_admin["headers"],
            status=403,
        )

    def test_update_fails_without_id_and_resource_id(self, app, setup_data):
        """Sin id ni resource_id no se puede resolver el dataset (mensaje claro)."""
        app.post(
            self._api("iati_file_update"),
            params={"namespace": "x"},  # falta id y resource_id
            headers=setup_data.user_admin["headers"],
            status=403,
        )

    # --- EJECUCIÓN / CAMPOS ---------------------------------------------------

    def test_update_accepts_file_type_by_name_and_int(self, app, setup_data):
        created = self._create_file(app, setup_data.sysadmin["headers"], setup_data.res["id"])

        # Cambiar por nombre
        resp = app.post(
            self._api("iati_file_update"),
            params={"id": created["id"], "file_type": IATIFileTypes.ORGANIZATION_NAMES_FILE.name},
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]
        assert resp["file_type"] == IATIFileTypes.ORGANIZATION_NAMES_FILE.name

        # Cambiar por int (valor del enum)
        resp2 = app.post(
            self._api("iati_file_update"),
            params={"id": created["id"], "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.value},
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]
        assert resp2["file_type"] == IATIFileTypes.ORGANIZATION_MAIN_FILE.name

    def test_update_toggle_is_valid_and_last_error(self, app, setup_data):
        created = self._create_file(app, setup_data.sysadmin["headers"], setup_data.res["id"])

        # Marcar inválido con error
        resp = app.post(
            self._api("iati_file_update"),
            params={"id": created["id"], "is_valid": False, "last_error": "boom"},
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]
        assert resp["is_valid"] is False
        assert resp["last_error"] == "boom"

        # Marcar válido y limpiar error
        resp2 = app.post(
            self._api("iati_file_update"),
            params={"id": created["id"], "is_valid": True, "last_error": None},
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]
        assert resp2["is_valid"] is True
        assert resp2["last_error"] is None

        # Confirma en DB
        obj = model.Session.query(IATIFile).get(created["id"])
        assert obj.is_valid is True
        assert obj.last_error is None
