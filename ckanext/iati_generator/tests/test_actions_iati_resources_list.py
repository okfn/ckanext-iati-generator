from types import SimpleNamespace
import pytest

from ckan.tests import helpers, factories
from ckan import model

from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.tests.factories import IATIFileFactory


@pytest.fixture
def setup_data():
    obj = SimpleNamespace()

    # users
    obj.sysadmin = factories.Sysadmin()

    # organization + dataset + resource
    obj.org = factories.Organization()
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
class TestIatiResourcesList:

    def test_iati_resources_list_returns_expected_row(self, setup_data):
        """
        iati_resources_list should return a row with:
            - correct namespace
            - correct resource/dataset
            - iati_file info (file_type, is_valid, last_error) properly mapped
        """

        # Create an IATIFile linked to the resource
        IATIFileFactory(
            file_type=IATIFileTypes.ORGANIZATION_EXPENDITURE_FILE.value,
            is_valid=False,
            last_error="boom!",
        )
        # Context as sysadmin (to pass the check_access)
        context = {"user": setup_data.sysadmin["name"]}

        result = helpers.call_action(
            "iati_resources_list",
            context=context,
        )

        # Only one IATIFile, so count = 1 and a single row
        assert result["count"] == 1
        row = result["results"][0]

        # Namespace and resource/dataset links
        assert row["namespace"] == DEFAULT_NAMESPACE
        assert row["resource"]["id"] == setup_data.res["id"]
        assert row["dataset"]["id"] == setup_data.pkg["id"]

        # iati_file data
        iati_info = row["iati_file"]
        assert iati_info["file_type"] == IATIFileTypes.ORGANIZATION_EXPENDITURE_FILE.name
        assert iati_info["is_valid"] is False
        assert iati_info["last_error"] == "boom!"

    def test_iati_resources_list_no_iati_file_info(self, setup_data):
        """
        If there is no IATIFile linked to the resource, the returned row
        should have is_valid = False and last_error = None
        """
        # Context as sysadmin (to pass the check_access)
        context = {"user": setup_data.sysadmin["name"]}

        result = helpers.call_action(
            "iati_resources_list",
            context=context,
        )

        # Without IATIFiles, should return 0 results
        assert result["count"] == 0
        assert result["results"] == []

    def test_iati_resources_list_valid_file_with_success_date(self, setup_data):
        """
        Verify that last_processed_success is returned correctly
        when is_valid=True
        """
        from datetime import datetime

        # Create an IATIFile with success date using the factory
        IATIFileFactory(
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE.value,
            is_valid=True,
            last_processed_success=datetime(2025, 11, 27, 10, 30),
            resource_id=setup_data.res["id"]
        )

        context = {"user": setup_data.sysadmin["name"]}
        result = helpers.call_action("iati_resources_list", context=context)

        assert result["count"] == 1
        row = result["results"][0]
        iati_info = row["iati_file"]

        assert iati_info["is_valid"] is True
        assert iati_info["last_error"] is None
        assert iati_info["last_processed_success"].startswith("2025-11-27")
        assert iati_info["file_type"] == IATIFileTypes.ORGANIZATION_MAIN_FILE.name

    def test_iati_resources_list_multiple_files(self, setup_data):
        """
        Verify that multiple IATIFiles are returned correctly
        and that they are ordered
        """
        session = model.Session

        # Create second resource and dataset
        pkg2 = factories.Dataset(owner_org=setup_data.org["id"], name="dataset-b")
        res2 = factories.Resource(
            package_id=pkg2["id"],
            format="CSV",
            name="aaa-file.csv",
        )

        # First IATIFile
        iati1 = IATIFileFactory(
            namespace=DEFAULT_NAMESPACE,
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE.value,
            resource_id=setup_data.res["id"],
            is_valid=True,
        )

        # Second IATIFile (should appear first due to ordering)
        iati2 = IATIFileFactory(
            namespace=DEFAULT_NAMESPACE,
            file_type=IATIFileTypes.ORGANIZATION_EXPENDITURE_FILE.value,
            resource_id=res2["id"],
            is_valid=False,
            last_error="Error en el segundo",
        )

        session.add_all([iati1, iati2])
        session.commit()

        context = {"user": setup_data.sysadmin["name"]}
        result = helpers.call_action("iati_resources_list", context=context)

        assert result["count"] == 2

        # Verify ordering: by dataset name, then resource name, then file_type
        # dataset-b comes first alphabetically
        first = result["results"][0]
        assert first["dataset"]["name"] == "dataset-b"
        assert first["resource"]["id"] == res2["id"]

    def test_iati_resources_list_different_namespaces(self, setup_data):
        """
        Verify that multiple namespaces are handled correctly
        """

        # IATIFile with custom namespace using factory
        IATIFileFactory(
            namespace="custom-ns",
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE.value,
            resource_id=setup_data.res["id"],
        )

        context = {"user": setup_data.sysadmin["name"]}
        result = helpers.call_action("iati_resources_list", context=context)

        assert result["count"] == 1
        row = result["results"][0]
        assert row["namespace"] == "custom-ns"

    def test_iati_resources_list_resource_fields(self, setup_data):
        """
        Verify that all resource fields are returned correctly
        """

        IATIFileFactory(
            namespace=DEFAULT_NAMESPACE,
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE.value,
            resource_id=setup_data.res["id"],
        )

        context = {"user": setup_data.sysadmin["name"]}
        result = helpers.call_action("iati_resources_list", context=context)

        row = result["results"][0]
        resource = row["resource"]

        assert resource["id"] == setup_data.res["id"]
        assert resource["name"] == "file.csv"
        assert resource["format"] == "CSV"
        assert "url" in resource
        assert "description" in resource

    def test_iati_resources_list_dataset_fields(self, setup_data):
        """
        Verify that all dataset fields are returned correctly
        """

        IATIFileFactory(
            namespace=DEFAULT_NAMESPACE,
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE.value,
            resource_id=setup_data.res["id"],
        )

        context = {"user": setup_data.sysadmin["name"]}
        result = helpers.call_action("iati_resources_list", context=context)

        row = result["results"][0]
        dataset = row["dataset"]

        assert dataset["id"] == setup_data.pkg["id"]
        assert dataset["name"] == setup_data.pkg["name"]
        assert dataset["title"] == setup_data.pkg["title"]
        assert dataset["owner_org"] == setup_data.org["id"]
