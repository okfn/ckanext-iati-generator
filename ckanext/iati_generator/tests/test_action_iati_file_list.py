from types import SimpleNamespace
import pytest
from ckan.tests import helpers, factories
from ckanext.iati_generator.models.enums import IATIFileTypes


@pytest.fixture
def setup_data():
    """Crea usuarios, org, dataset y resource base — con tokens+headers listos."""
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

    # Org con roles
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
        package_id=obj.pkg["id"],
        format="CSV",
        url_type="upload",
        url="test.csv",
        name="test.csv",
    )
    return obj


@pytest.mark.ckan_config("ckan.plugins", "iati_generator")
@pytest.mark.usefixtures("clean_db")
class TestIatiFileListAction:

    def _make_pkg_res(self):
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

    def _create_iati_file(self, resource_id, file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE.value, is_valid=True, namespace="iati-xml"):
        """Helper to create an IATIFile row for a resource."""
        # usamos la acción pública de creación para asegurar integridad
        sys = factories.Sysadmin()
        context = {"user": sys["name"]}
        return helpers.call_action(
            "iati_file_create",
            context=context,
            resource_id=resource_id,
            file_type=file_type,
            namespace=namespace,
            is_valid=is_valid,
        )

    def test_list_returns_items_and_fields(self):
        """Test that the action returns IATI files with expected fields."""
        org, pkg, res = self._make_pkg_res()
        self._create_iati_file(res["id"], file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE.value)

        # sysadmin llama a la acción
        sys = factories.Sysadmin()
        context = {"user": sys["name"]}
        out = helpers.call_action("iati_file_list", context=context)

        assert out["count"] >= 1
        item = out["results"][0]
        assert "id" in item and "file_type" in item and "resource" in item and "dataset" in item
        assert item["file_type"] in (IATIFileTypes.ORGANIZATION_MAIN_FILE.name, IATIFileTypes.ORGANIZATION_NAMES_FILE.name)

    def test_filter_by_file_type_string_and_valid_flag(self):
        """Test filtering by file_type (string) and valid (boolean)."""
        _, _, res1 = self._make_pkg_res()
        _, _, res2 = self._make_pkg_res()

        self._create_iati_file(res1["id"], file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE.value, is_valid=True)
        self._create_iati_file(res2["id"], file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE.value, is_valid=False)

        sys = factories.Sysadmin()
        context = {"user": sys["name"]}

        # filtra por tipo (nombre del enum) + valid=true
        out = helpers.call_action(
            "iati_file_list",
            context=context,
            file_type="ORGANIZATION_MAIN_FILE",
            valid="true",
        )
        assert out["count"] == 1
        assert out["results"][0]["file_type"] == "ORGANIZATION_MAIN_FILE"
        assert out["results"][0]["is_valid"] is True

    def test_requires_sysadmin(self):
        """Only sysadmin users can call this action."""
        _, _, res = self._make_pkg_res()
        self._create_iati_file(res["id"])

        user = factories.User()
        context = {"user": user["name"]}

        with pytest.raises(Exception):
            helpers.call_action("iati_file_list", context=context)

    def test_pagination(self):
        """Test start/rows pagination parameters."""
        # Crear varios items
        for _ in range(3):
            _, _, res = self._make_pkg_res()
            self._create_iati_file(res["id"])

        sys = factories.Sysadmin()
        context = {"user": sys["name"]}

        out1 = helpers.call_action("iati_file_list", context=context, start=0, rows=2)
        out2 = helpers.call_action("iati_file_list", context=context, start=2, rows=2)

        assert out1["count"] >= 3
        assert len(out1["results"]) == 2
        assert len(out2["results"]) >= 1
