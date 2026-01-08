from types import SimpleNamespace
import pytest
from ckan.tests import helpers, factories
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.tests.factories import create_iati_file
from ckan.lib.helpers import url_for


@pytest.fixture
def setup_data_with_namespaces():
    """Create users, org, datasets and resources with different namespaces."""
    obj = SimpleNamespace()

    # Users + tokens
    obj.sysadmin = factories.SysadminWithToken()
    obj.sysadmin["headers"] = {"Authorization": obj.sysadmin["token"]}
    obj.user_admin = factories.UserWithToken()
    obj.user_admin["headers"] = {"Authorization": obj.user_admin["token"]}

    # Org with roles
    obj.org = factories.Organization(
        users=[
            {"name": obj.user_admin["name"], "capacity": "admin"},
        ]
    )

    # Create multiple datasets and resources
    obj.pkg1 = factories.Dataset(owner_org=obj.org["id"], title="Dataset 1")
    obj.res1 = factories.Resource(
        package_id=obj.pkg1["id"],
        format="CSV",
        url_type="upload",
        url="test1.csv",
        name="Resource Namespace A",
    )

    obj.pkg2 = factories.Dataset(owner_org=obj.org["id"], title="Dataset 2")
    obj.res2 = factories.Resource(
        package_id=obj.pkg2["id"],
        format="CSV",
        url_type="upload",
        url="test2.csv",
        name="Resource Namespace B",
    )

    obj.pkg3 = factories.Dataset(owner_org=obj.org["id"], title="Dataset 3")
    obj.res3 = factories.Resource(
        package_id=obj.pkg3["id"],
        format="CSV",
        url_type="upload",
        url="test3.csv",
        name="Resource Namespace A Again",
    )

    obj.pkg4 = factories.Dataset(owner_org=obj.org["id"], title="Dataset 4")
    obj.res4 = factories.Resource(
        package_id=obj.pkg4["id"],
        format="CSV",
        url_type="upload",
        url="test4.csv",
        name="Resource Namespace C",
    )

    return obj


@pytest.mark.usefixtures('with_plugins', 'clean_db')
class TestNamespaceFilter:
    """Tests for namespace filtering in iati_file_list action and admin view."""

    # ---- Helper methods ----
    def _call_action_as_user(self, action, user_name, **data):
        """Call an action with a specific user context."""
        context = {"user": user_name}
        return helpers.call_action(action, context=context, **data)

    # ---- Tests for iati_file_list action ----

    def test_list_all_namespaces_without_filter(self, setup_data_with_namespaces):
        """Test that without namespace filter, all IATI files are returned."""
        setup = setup_data_with_namespaces

        # Create IATI files with different namespaces
        create_iati_file(
            resource_id=setup.res1["id"],
            namespace="iati-xml",
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )
        create_iati_file(
            resource_id=setup.res2["id"],
            namespace="iati-json",
            file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE,
        )
        create_iati_file(
            resource_id=setup.res3["id"],
            namespace="iati-xml",
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )

        # Call action without namespace filter
        result = self._call_action_as_user(
            "iati_file_list",
            setup.sysadmin["name"]
        )

        assert result["count"] == 3
        assert len(result["results"]) == 3

        # Verify different namespaces are present
        namespaces = {item["namespace"] for item in result["results"]}
        assert "iati-xml" in namespaces
        assert "iati-json" in namespaces

    def test_filter_by_specific_namespace(self, setup_data_with_namespaces):
        """Test filtering by a specific namespace returns only matching files."""
        setup = setup_data_with_namespaces

        # Create IATI files with different namespaces
        create_iati_file(
            resource_id=setup.res1["id"],
            namespace="iati-xml",
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )
        create_iati_file(
            resource_id=setup.res2["id"],
            namespace="iati-json",
            file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE,
        )
        create_iati_file(
            resource_id=setup.res3["id"],
            namespace="iati-xml",
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )
        create_iati_file(
            resource_id=setup.res4["id"],
            namespace="custom-namespace",
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )

        # Filter by iati-xml namespace
        result = self._call_action_as_user(
            "iati_file_list",
            setup.sysadmin["name"],
            namespace="iati-xml"
        )

        assert result["count"] == 2
        assert len(result["results"]) == 2

        # All results should have iati-xml namespace
        for item in result["results"]:
            assert item["namespace"] == "iati-xml"

    def test_filter_by_empty_namespace_returns_all(self, setup_data_with_namespaces):
        """Test that empty string namespace filter returns all files."""
        setup = setup_data_with_namespaces

        # Create IATI files
        create_iati_file(
            resource_id=setup.res1["id"],
            namespace="iati-xml",
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )
        create_iati_file(
            resource_id=setup.res2["id"],
            namespace="iati-json",
            file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE,
        )

        # Filter with empty namespace (should return all)
        result = self._call_action_as_user(
            "iati_file_list",
            setup.sysadmin["name"],
            namespace=""
        )

        assert result["count"] == 2

    def test_filter_nonexistent_namespace_returns_empty(self, setup_data_with_namespaces):
        """Test filtering by a namespace that doesn't exist returns no results."""
        setup = setup_data_with_namespaces

        # Create IATI files
        create_iati_file(
            resource_id=setup.res1["id"],
            namespace="iati-xml",
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )

        # Filter by non-existent namespace
        result = self._call_action_as_user(
            "iati_file_list",
            setup.sysadmin["name"],
            namespace="non-existent-namespace"
        )

        assert result["count"] == 0
        assert len(result["results"]) == 0

    # ---- Tests for iati_resources_list action ----

    def test_resources_list_filter_by_namespace(self, setup_data_with_namespaces):
        """Test iati_resources_list action filters by namespace."""
        setup = setup_data_with_namespaces

        # Create IATI files with different namespaces
        create_iati_file(
            resource_id=setup.res1["id"],
            namespace="iati-xml",
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )
        create_iati_file(
            resource_id=setup.res2["id"],
            namespace="iati-json",
            file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE,
        )

        # Filter by namespace
        result = self._call_action_as_user(
            "iati_resources_list",
            setup.sysadmin["name"],
            namespace="iati-xml"
        )

        # Should only return iati-xml resources
        assert result["count"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["iati_file"]["namespace"] == "iati-xml"

    # ---- Tests for admin view ----

    def test_admin_view_namespace_filter_displays_correctly(self, app, setup_data_with_namespaces):
        """Test that the admin view displays namespace filter and filters correctly."""
        setup = setup_data_with_namespaces

        # Create IATI files
        create_iati_file(
            resource_id=setup.res1["id"],
            namespace="iati-xml",
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )
        create_iati_file(
            resource_id=setup.res2["id"],
            namespace="iati-json",
            file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE,
        )

        url = url_for("iati_generator_admin_files.iati_files_index")
        auth = {"Authorization": setup.sysadmin["token"]}

        # Test without filter - should show all
        resp = app.get(url, headers=auth)
        assert resp.status_code == 200
        assert "Resource Namespace A" in resp.body
        assert "Resource Namespace B" in resp.body

        # Test with namespace filter
        resp_filtered = app.get(url + "?namespace=iati-xml", headers=auth)
        assert resp_filtered.status_code == 200
        assert "Resource Namespace A" in resp_filtered.body
        assert "Resource Namespace B" not in resp_filtered.body

    def test_admin_view_namespace_dropdown_shows_all_namespaces(self, app, setup_data_with_namespaces):
        """Test that namespace dropdown includes all distinct namespaces."""
        setup = setup_data_with_namespaces

        # Create IATI files with different namespaces
        create_iati_file(
            resource_id=setup.res1["id"],
            namespace="iati-xml",
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )
        create_iati_file(
            resource_id=setup.res2["id"],
            namespace="iati-json",
            file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE,
        )
        create_iati_file(
            resource_id=setup.res3["id"],
            namespace="custom-namespace",
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )

        url = url_for("iati_generator_admin_files.iati_files_index")
        auth = {"Authorization": setup.sysadmin["token"]}

        resp = app.get(url, headers=auth)
        assert resp.status_code == 200

        # Check that namespace options are present in the dropdown
        assert 'name="namespace"' in resp.body
        assert "iati-xml" in resp.body
        assert "iati-json" in resp.body
        assert "custom-namespace" in resp.body

    def test_admin_view_namespace_filter_empty_returns_all(self, app, setup_data_with_namespaces):
        """Test that selecting 'All' in namespace filter shows all files."""
        setup = setup_data_with_namespaces

        # Create IATI files
        create_iati_file(
            resource_id=setup.res1["id"],
            namespace="iati-xml",
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )
        create_iati_file(
            resource_id=setup.res2["id"],
            namespace="iati-json",
            file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE,
        )

        url = url_for("iati_generator_admin_files.iati_files_index")
        auth = {"Authorization": setup.sysadmin["token"]}

        # Request with empty namespace (All option)
        resp = app.get(url + "?namespace=", headers=auth)
        assert resp.status_code == 200

        # Should show both resources
        assert "Resource Namespace A" in resp.body
        assert "Resource Namespace B" in resp.body

    def test_namespace_filter_preserves_selected_value(self, app, setup_data_with_namespaces):
        """Test that the selected namespace is preserved in the dropdown."""
        setup = setup_data_with_namespaces

        # Create IATI file
        create_iati_file(
            resource_id=setup.res1["id"],
            namespace="iati-xml",
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )

        url = url_for("iati_generator_admin_files.iati_files_index")
        auth = {"Authorization": setup.sysadmin["token"]}

        # Request with namespace filter
        resp = app.get(url + "?namespace=iati-xml", headers=auth)
        assert resp.status_code == 200

        # The selected option should have the 'selected' attribute
        assert 'value="iati-xml"' in resp.body
        assert 'selected' in resp.body
