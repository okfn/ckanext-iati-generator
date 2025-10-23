from types import SimpleNamespace
import pytest
from ckan.tests import helpers, factories
from ckan.plugins import toolkit
from ckanext.iati_generator.models.enums import IATIFileTypes


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

    def _create_iati_file(self, user_name, resource_id,
                          file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE.value,
                          is_valid=True, namespace="iati-xml"):
        """Create an IATIFile using the public action (ensures validations)."""
        context = {"user": user_name}
        return helpers.call_action(
            "iati_file_create",
            context=context,
            resource_id=resource_id,
            file_type=file_type,
            namespace=namespace,
            is_valid=is_valid,
        )

    # ---- helpers for calling actions
    def _call_action_as_user(self, action, user_name, **data):
        """Call an action with a specific user context."""
        context = {"user": user_name}
        return helpers.call_action(action, context=context, **data)

    # ---------- tests ----------
    def test_list_returns_items_and_fields(self, setup_data):
        """Test that the action returns IATI files with expected fields."""

        # Create 1 IATIFile
        self._create_iati_file(setup_data.sysadmin["name"], setup_data.res["id"])

        # Sysadmin calls the action
        result = self._call_action_as_user("iati_file_list", setup_data.sysadmin["name"])

        assert result["count"] == 1
        # Test exactly what we expect here
        item = result["results"][0]
        assert {"id", "file_type", "resource", "dataset"} <= set(item.keys())
        assert item["file_type"] == IATIFileTypes.ORGANIZATION_MAIN_FILE.name

    def test_filter_by_file_type_string_and_valid_flag(self, setup_data):
        """Test filtering by file_type (string) and valid (boolean)."""
        # Two distinct IATIFiles
        self._create_iati_file(
            setup_data.sysadmin["name"],
            setup_data.res["id"],
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE.value,
            is_valid=True,
        )

        # Create another dataset+resource for the second file
        pkg2 = factories.Dataset(owner_org=setup_data.org["id"])
        res2 = factories.Resource(
            package_id=pkg2["id"], format="CSV", url_type="upload", url="b.csv", name="b.csv"
        )
        self._create_iati_file(
            setup_data.sysadmin["name"],
            res2["id"],
            file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE.value,
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
        self._create_iati_file(setup_data.sysadmin["name"], setup_data.res["id"])

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
            self._create_iati_file(setup_data.sysadmin["name"], res["id"])

        # page 1
        result1 = self._call_action_as_user("iati_file_list", setup_data.sysadmin["name"], start=0, rows=2)
        # page 2
        result2 = self._call_action_as_user("iati_file_list", setup_data.sysadmin["name"], start=2, rows=2)

        assert result1["count"] == 3
        assert len(result1["results"]) == 2
        assert len(result2["results"]) == 1
