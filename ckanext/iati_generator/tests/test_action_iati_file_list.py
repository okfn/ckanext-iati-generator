from types import SimpleNamespace
import pytest
from ckan.tests import helpers, factories
from ckan.plugins import toolkit
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.tests.factories import create_iati_file


@pytest.fixture
def setup_data():
    """Create users, org, dataset and base resource — with tokens+headers ready."""
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

    # Org with roles
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


@pytest.mark.usefixtures('with_plugins', 'clean_db')
class TestIatiFileListAction:

    # ---- helpers for calling actions
    def _call_action_as_user(self, action, user_name, **data):
        """Call an action with a specific user context."""
        context = {"user": user_name, "ignore_auth": False}
        return helpers.call_action(action, context=context, **data)

    # ---------- tests ----------
    def test_list_returns_items_and_fields(self, setup_data):
        """Test that the action returns IATI files with expected fields."""

        # Create 1 IATIFile
        create_iati_file(resource_id=setup_data.res["id"])

        # Sysadmin calls the action
        result = self._call_action_as_user("iati_file_list", setup_data.sysadmin["name"])

        assert result["count"] == 1
        # Test exactly what we expect here (shape + a couple of values)
        item = result["results"][0]
        assert set(item.keys()) == {
            "id", "namespace", "file_type", "is_valid", "last_success", "last_error",
            "resource", "dataset"
        }
        # nested shapes
        assert set(item["resource"].keys()) == {"id", "name", "format", "url", "description"}
        assert set(item["dataset"].keys()) == {"id", "name", "title", "owner_org"}
        # sample values
        assert item["file_type"] == IATIFileTypes.ORGANIZATION_MAIN_FILE.name
        assert item["is_valid"] in (True, False)
        assert item["resource"]["id"]
        assert item["dataset"]["id"]

    def test_filter_by_file_type_string_and_valid_flag(self, setup_data):
        """Test filtering by file_type (string) and valid (boolean)."""
        # Two distinct IATIFiles
        create_iati_file(
            resource_id=setup_data.res["id"],
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
            is_valid=True,
        )

        # Create another dataset+resource for the second file
        pkg2 = factories.Dataset(owner_org=setup_data.org["id"])
        res2 = factories.Resource(
            package_id=pkg2["id"], format="CSV", url_type="upload", url="b.csv", name="b.csv"
        )
        create_iati_file(
            resource_id=res2["id"],
            file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE,
            is_valid=False,
        )

        # Filter: type by name + valid=true
        result = self._call_action_as_user(
            "iati_file_list",
            setup_data.sysadmin["name"],
            file_type="ORGANIZATION_MAIN_FILE",
            valid="true",
        )
        assert result["count"] == 1
        assert result["results"][0]["file_type"] == "ORGANIZATION_MAIN_FILE"
        assert result["results"][0]["is_valid"] is True

    def test_requires_sysadmin(self, setup_data):
        """Only sysadmin users can call this action."""

        # Ensure at least one record exists
        create_iati_file(resource_id=setup_data.res["id"])

        # Regular user tries to list - should raise authorization error
        with pytest.raises(toolkit.NotAuthorized):
            self._call_action_as_user("iati_file_list", setup_data.user_editor["name"])

    def test_pagination(self, setup_data):
        """Test start/rows pagination parameters."""
        # Generate several items
        for _ in range(3):
            pkg = factories.Dataset(owner_org=setup_data.org["id"])
            res = factories.Resource(
                package_id=pkg["id"], format="CSV", url_type="upload", url="x.csv", name="x.csv"
            )
            create_iati_file(resource_id=res["id"])

        # page 1
        result1 = self._call_action_as_user("iati_file_list", setup_data.sysadmin["name"], start=0, rows=2)
        # page 2
        result2 = self._call_action_as_user("iati_file_list", setup_data.sysadmin["name"], start=2, rows=2)

        assert result1["count"] == 3
        assert len(result1["results"]) == 2
        assert len(result2["results"]) == 1
