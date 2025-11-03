import pytest
from ckan.tests import factories

from ckanext.iati_generator.tests.factories import create_iati_file
from ckanext.iati_generator.models.enums import IATIFileTypes


@pytest.mark.ckan_config("ckan.plugins", "iati_generator")
@pytest.mark.usefixtures("clean_db")
class TestServePublicIati:

    def _create_dataset_with_resource(self, url="http://example.com/iati/organization.xml"):
        """Helper to create a dataset with one resource."""
        pkg = factories.Dataset()
        res = factories.Resource(
            package_id=pkg["id"],
            url=url,
            format="XML",
            state="active",
        )
        return pkg, res

    def test_redirects_to_resource_url_when_file_exists(self, app):
        """When the IATIFile exists, redirect to the resource URL."""
        _, res = self._create_dataset_with_resource()
        # Create an IATIFile entry that matches namespace + file_type + resource_id
        create_iati_file(
            namespace="bcie",
            resource_id=res["id"],
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
            is_valid=True,
        )

        resp = app.get("/iati/bcie/organization.xml", status=302, follow_redirects=False)
        assert resp.headers["Location"] == res["url"]

    def test_returns_404_when_unknown_filename(self, app):
        """When the filename is not recognized, respond with 404."""
        # The endpoint only recognizes organization.xml (and activities.xml if enabled)
        app.get("/iati/bcie/unknown.xml", status=404)

    def test_returns_404_when_no_file_for_namespace(self, app):
        """When the IATIFile does not exist for the given namespace, respond 404."""
        # Resource exists, but the IATIFile is for a different namespace
        _, res = self._create_dataset_with_resource()
        create_iati_file(
            namespace="otro",
            resource_id=res["id"],
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )
        app.get("/iati/bcie/organization.xml", status=404)

    def test_returns_404_when_resource_has_no_url(self, app):
        """When the resource has no URL, respond with 404."""
        pkg = factories.Dataset()
        res = factories.Resource(
            package_id=pkg["id"],
            url="",      # sin URL
            format="XML",
            state="active",
        )
        create_iati_file(
            namespace="bcie",
            resource_id=res["id"],
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
        )
        app.get("/iati/bcie/organization.xml", status=404)
