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
        """Convierte user_id en admin de la organización usando la API (requiere token sysadmin)."""
        sys = factories.SysadminWithToken()
        headers = {"Authorization": sys["token"]}
        params = {
            "id": org_id,
            "object": user_id,
            "object_type": "user",
            "capacity": "admin",
        }
        # status=200 incluso si ya existe devuelve OK/Conflict controlado por CKAN;
        # para tests es suficiente que no explote.
        app.post(self._api("member_create"), headers=headers, params=params, status=200)

    def test_create_denied_for_regular_user(self, app):
        """Un usuario normal no puede crear un IATIFile."""
        user = factories.UserWithToken()
        org, pkg, res = self._make_dataset_with_resource()

        payload = {
            "resource_id": res["id"],
            "package_id": pkg["id"],
            "file_type": IATIFileTypes.ORGANIZATION_MAIN_FILE.name,
        }
        headers = {"Authorization": user["token"]}
        app.post(self._api("iati_file_create"), params=payload, headers=headers, status=403)

    def test_create_allowed_for_sysadmin(self, app):
        """Un sysadmin puede crear un IATIFile."""
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
        """Un admin de la org dueña del dataset puede crear un IATIFile"""
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
        """Un admin de la org dueña del dataset puede actualizar un IATIFile"""
        # Crear IATIFile como sysadmin
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

        # Hacer admin de la org a un user normal y actualizar por ID del IATIFile
        user = factories.UserWithToken()
        self._make_org_admin(app, org["id"], user["id"])
        upd_headers = {"Authorization": user["token"]}
        resp = app.post(
            self._api("iati_file_update"),
            params={"id": created["id"], "package_id": pkg["id"], "is_valid": True},
            headers=upd_headers,
            status=200,
        )
        assert resp.json["success"] is True
        assert resp.json["result"]["is_valid"] is True

    def test_delete_denied_for_regular_user(self, app):
        """Un usuario normal no puede borrar un IATIFile."""
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
        """Cualquiera puede ver un IATIFile si conoce su ID."""
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

        # sin Authorization → debe permitir show
        resp = app.post(self._api("iati_file_show"), params={"id": created["id"]}, status=200)
        assert resp.json["success"] is True
        assert resp.json["result"]["id"] == created["id"]
