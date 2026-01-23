from datetime import datetime, timedelta

import pytest
from ckan.tests import factories
from ckanext.iati_generator.models.enums import IATIFileTypes


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPublicIatiEndpoints:
    
    def test_org_redirects_to_final_org_file(self, app):
        """
        /iati/<namespace>/organisation.xml should redirect to the
        resource with iati_file_type=FINAL_ORGANIZATION_FILE.
        """
        namespace = "test-namespace-org"
        
        # Create a dataset with the namespace
        dataset = factories.Dataset(
            extras=[{"key": "iati_namespace", "value": namespace}]
        )
        
        # Create resources - only the FINAL should be returned
        factories.Resource(
            package_id=dataset["id"],
            url="http://example.org/organisations.csv",
            iati_file_type=str(IATIFileTypes.ORGANIZATION_MAIN_FILE.value)
        )
        
        final_org_res = factories.Resource(
            package_id=dataset["id"],
            url="http://example.org/organisation.xml",
            iati_file_type=str(IATIFileTypes.FINAL_ORGANIZATION_FILE.value)
        )
        
        # Call the public endpoint
        res = app.get(
            f"/iati/{namespace}/organisation.xml",
            status=302,
            follow_redirects=False,
        )
        
        assert res.status_code == 302
        assert res.headers["Location"] == final_org_res["url"]

    def test_org_returns_404_when_no_final_file(self, app):
        """
        Should return 404 when dataset exists but has no FINAL_ORGANIZATION_FILE resource.
        """
        namespace = "test-namespace-org-no-final"
        
        dataset = factories.Dataset(
            extras=[{"key": "iati_namespace", "value": namespace}]
        )
        
        # Create only a non-final resource
        factories.Resource(
            package_id=dataset["id"],
            url="http://example.org/organisations.csv",
            iati_file_type=str(IATIFileTypes.ORGANIZATION_MAIN_FILE.value)
        )
        
        res = app.get(
            f"/iati/{namespace}/organisation.xml",
            status=404,
        )
        assert res.status_code == 404

    def test_org_returns_404_when_no_dataset(self, app):
        """
        Should return 404 when no dataset exists for the namespace.
        """
        namespace = "no-such-namespace"
        res = app.get(f"/iati/{namespace}/organisation.xml", status=404)
        assert res.status_code == 404

    def test_activities_redirects_to_final_activity_file(self, app):
        """
        /iati/<namespace>/activity.xml should redirect to the
        resource with iati_file_type=FINAL_ACTIVITY_FILE.
        """
        namespace = "test-namespace-act"
        
        dataset = factories.Dataset(
            extras=[{"key": "iati_namespace", "value": namespace}]
        )
        
        # Create various activity resources
        factories.Resource(
            package_id=dataset["id"],
            url="http://example.org/activities.csv",
            iati_file_type=str(IATIFileTypes.ACTIVITY_MAIN_FILE.value)
        )
        
        final_act_res = factories.Resource(
            package_id=dataset["id"],
            url="http://example.org/activity.xml",
            iati_file_type=str(IATIFileTypes.FINAL_ACTIVITY_FILE.value)
        )
        
        res = app.get(
            f"/iati/{namespace}/activity.xml",
            status=302,
            follow_redirects=False,
        )
        
        assert res.status_code == 302
        assert res.headers["Location"] == final_act_res["url"]

    def test_activities_returns_404_when_no_final_file(self, app):
        """
        Should return 404 when dataset exists but has no FINAL_ACTIVITY_FILE resource.
        """
        namespace = "test-namespace-act-no-final"
        
        dataset = factories.Dataset(
            extras=[{"key": "iati_namespace", "value": namespace}]
        )
        
        factories.Resource(
            package_id=dataset["id"],
            url="http://example.org/activities.csv",
            iati_file_type=str(IATIFileTypes.ACTIVITY_MAIN_FILE.value)
        )
        
        res = app.get(
            f"/iati/{namespace}/activity.xml",
            status=404,
        )
        assert res.status_code == 404

    def test_activities_returns_404_when_no_dataset(self, app):
        """
        Should return 404 when no dataset exists for the namespace.
        """
        namespace = "no-such-namespace-act"
        res = app.get(
            f"/iati/{namespace}/activity.xml",
            status=404,
        )
        assert res.status_code == 404

    def test_namespace_with_spaces(self, app):
        """
        Should work with namespaces that contain spaces.
        """
        namespace = "test namespace with spaces"
        
        dataset = factories.Dataset(
            extras=[{"key": "iati_namespace", "value": namespace}]
        )
        
        final_act_res = factories.Resource(
            package_id=dataset["id"],
            url="http://example.org/activity.xml",
            iati_file_type=str(IATIFileTypes.FINAL_ACTIVITY_FILE.value)
        )
        
        res = app.get(
            f"/iati/{namespace}/activity.xml",
            status=302,
            follow_redirects=False,
        )
        
        assert res.status_code == 302
        assert res.headers["Location"] == final_act_res["url"]
