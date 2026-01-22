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

    def test_namespace_normalization_with_hyphens(self, app):
        """
        Should find dataset when namespace is normalized (spaces -> hyphens).
        Dataset has 'test-namespace' but request comes with 'test namespace'.
        """
        namespace_in_db = "test-normalized-namespace"
        namespace_in_request = "test normalized namespace"

        dataset = factories.Dataset(
            extras=[{"key": "iati_namespace", "value": namespace_in_db}]
        )

        final_act_res = factories.Resource(
            package_id=dataset["id"],
            url="http://example.org/activity.xml",
            iati_file_type=str(IATIFileTypes.FINAL_ACTIVITY_FILE.value)
        )

        # Request with spaces should find dataset with hyphens
        res = app.get(
            f"/iati/{namespace_in_request}/activity.xml",
            status=302,
            follow_redirects=False,
        )

        assert res.status_code == 302
        assert res.headers["Location"] == final_act_res["url"]

    def test_multiple_final_files_returns_first_one(self, app):
        """
        If somehow there are multiple FINAL resources, should return the first one found.
        """
        namespace = "test-multiple-finals"

        dataset = factories.Dataset(
            extras=[{"key": "iati_namespace", "value": namespace}]
        )

        final_res_1 = factories.Resource(
            package_id=dataset["id"],
            url="http://example.org/activity1.xml",
            iati_file_type=str(IATIFileTypes.FINAL_ACTIVITY_FILE.value)
        )

        factories.Resource(
            package_id=dataset["id"],
            url="http://example.org/activity2.xml",
            iati_file_type=str(IATIFileTypes.FINAL_ACTIVITY_FILE.value)
        )

        res = app.get(
            f"/iati/{namespace}/activity.xml",
            status=302,
            follow_redirects=False,
        )

        assert res.status_code == 302
        # Should return the first one
        assert res.headers["Location"] == final_res_1["url"]

    def test_resource_without_iati_file_type_is_ignored(self, app):
        """
        Resources without iati_file_type should be ignored.
        """
        namespace = "test-no-file-type"

        dataset = factories.Dataset(
            extras=[{"key": "iati_namespace", "value": namespace}]
        )

        # Resource without iati_file_type
        factories.Resource(
            package_id=dataset["id"],
            url="http://example.org/random.csv"
        )

        final_org_res = factories.Resource(
            package_id=dataset["id"],
            url="http://example.org/organisation.xml",
            iati_file_type=str(IATIFileTypes.FINAL_ORGANIZATION_FILE.value)
        )

        res = app.get(
            f"/iati/{namespace}/organisation.xml",
            status=302,
            follow_redirects=False,
        )

        assert res.status_code == 302
        assert res.headers["Location"] == final_org_res["url"]

    def test_wrong_file_type_returns_404(self, app):
        """
        When requesting organisation.xml but only activity.xml exists, should return 404.
        """
        namespace = "test-wrong-type"

        dataset = factories.Dataset(
            extras=[{"key": "iati_namespace", "value": namespace}]
        )

        # Only activity file exists
        factories.Resource(
            package_id=dataset["id"],
            url="http://example.org/activity.xml",
            iati_file_type=str(IATIFileTypes.FINAL_ACTIVITY_FILE.value)
        )

        # Request organisation.xml
        res = app.get(
            f"/iati/{namespace}/organisation.xml",
            status=404,
        )

        assert res.status_code == 404

    def test_multiple_datasets_same_namespace_returns_first(self, app):
        """
        If multiple datasets have the same namespace (shouldn't happen but could),
        should return the first one found.
        """
        namespace = "duplicate-namespace"

        dataset1 = factories.Dataset(
            extras=[{"key": "iati_namespace", "value": namespace}]
        )

        dataset2 = factories.Dataset(
            extras=[{"key": "iati_namespace", "value": namespace}]
        )

        final_res_1 = factories.Resource(
            package_id=dataset1["id"],
            url="http://example.org/activity1.xml",
            iati_file_type=str(IATIFileTypes.FINAL_ACTIVITY_FILE.value)
        )

        factories.Resource(
            package_id=dataset2["id"],
            url="http://example.org/activity2.xml",
            iati_file_type=str(IATIFileTypes.FINAL_ACTIVITY_FILE.value)
        )

        res = app.get(
            f"/iati/{namespace}/activity.xml",
            status=302,
            follow_redirects=False,
        )

        assert res.status_code == 302
        # Should use the first dataset found
        assert res.headers["Location"] == final_res_1["url"]

    def test_case_sensitive_namespace(self, app):
        """
        Namespaces should be case-sensitive.
        """
        namespace_lower = "testnamespace"
        namespace_upper = "TestNamespace"

        dataset = factories.Dataset(
            extras=[{"key": "iati_namespace", "value": namespace_lower}]
        )

        factories.Resource(
            package_id=dataset["id"],
            url="http://example.org/activity.xml",
            iati_file_type=str(IATIFileTypes.FINAL_ACTIVITY_FILE.value)
        )

        # Request with different case should return 404
        res = app.get(
            f"/iati/{namespace_upper}/activity.xml",
            status=404,
        )

        assert res.status_code == 404
