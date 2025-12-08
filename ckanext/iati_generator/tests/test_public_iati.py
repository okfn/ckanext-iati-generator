from datetime import datetime, timedelta

import pytest
from ckan.tests import factories

from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.tests.factories import create_iati_file


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPublicIatiEndpoints:
    def test_org_redirects_to_latest_valid_file(self, app):
        """
        /iati/<namespace>/organization.xml should redirect to the
        most recent (last_processed_success) and valid (is_valid=True) resource.
        """
        namespace = "test-namespace-org"

        # Create two resources with different URLs
        older_res = factories.Resource(url="http://example.org/old_org.xml")
        newer_res = factories.Resource(url="http://example.org/new_org.xml")

        base_time = datetime(2025, 1, 1)

        # Older IATIFile
        create_iati_file(
            resource_id=older_res["id"],
            namespace=namespace,
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
            is_valid=True,
            last_processed_success=base_time,
        )

        # Newer IATIFile
        create_iati_file(
            resource_id=newer_res["id"],
            namespace=namespace,
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
            is_valid=True,
            last_processed_success=base_time + timedelta(days=1),
        )

        # Call the public endpoint (without authentication)
        res = app.get(
            f"/iati/{namespace}/organization.xml",
            status=302,
            follow_redirects=False,
        )
        assert res.status_code == 302
        # Should redirect to the newest resource
        assert res.headers["Location"] == newer_res["url"]

    def test_org_ignores_invalid_files(self, app):
        """
        Should ignore records with is_valid=False.
        """
        namespace = "test-namespace-org-invalid"

        invalid_res = factories.Resource(url="http://example.org/invalid_org.xml")
        valid_res = factories.Resource(url="http://example.org/valid_org.xml")

        base_time = datetime(2025, 1, 1)

        # INVALID file with newer date
        create_iati_file(
            resource_id=invalid_res["id"],
            namespace=namespace,
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
            is_valid=False,
            last_processed_success=base_time + timedelta(days=2),
        )

        # VALID file with older date
        create_iati_file(
            resource_id=valid_res["id"],
            namespace=namespace,
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
            is_valid=True,
            last_processed_success=base_time,
        )

        res = app.get(
            f"/iati/{namespace}/organization.xml",
            status=302,
            follow_redirects=False,
        )
        assert res.status_code == 302
        # Should choose the valid one, even though the invalid is newer
        assert res.headers["Location"] == valid_res["url"]

    def test_org_returns_404_when_no_files(self, app):
        """
        If there is no IATIFile for that namespace+type, should return 404.
        """
        namespace = "no-such-namespace"
        res = app.get(f"/iati/{namespace}/organization.xml", status=404)
        assert "No organization XML" in res.body

    def test_activities_redirects_to_latest_valid_file(self, app):
        """
        /iati/<namespace>/activities.xml should redirect to the last
        valid IATIFile of type ACTIVITY_MAIN_FILE.
        """
        namespace = "test-namespace-act"

        older_res = factories.Resource(url="http://example.org/old_act.xml")
        newer_res = factories.Resource(url="http://example.org/new_act.xml")

        base_time = datetime(2025, 1, 1)

        create_iati_file(
            resource_id=older_res["id"],
            namespace=namespace,
            file_type=IATIFileTypes.ACTIVITY_MAIN_FILE,
            is_valid=True,
            last_processed_success=base_time,
        )

        create_iati_file(
            resource_id=newer_res["id"],
            namespace=namespace,
            file_type=IATIFileTypes.ACTIVITY_MAIN_FILE,
            is_valid=True,
            last_processed_success=base_time + timedelta(days=1),
        )

        res = app.get(
            f"/iati/{namespace}/activities.xml",
            status=302,
            follow_redirects=False,
        )

        assert res.status_code == 302
        assert res.headers["Location"] == newer_res["url"]

    def test_activities_returns_404_when_no_files(self, app):
        """
        Should return 404 when no activity files exist for the namespace.
        """
        namespace = "no-such-namespace-act"
        res = app.get(
            f"/iati/{namespace}/activities.xml",
            status=404,
        )
        assert "No activities XML" in res.body

    def test_activities_ignores_invalid_files(self, app):
        """
        Should ignore records with is_valid=False for activities endpoint.
        """
        namespace = "test-namespace-act-invalid"

        invalid_res = factories.Resource(url="http://example.org/invalid_act.xml")
        valid_res = factories.Resource(url="http://example.org/valid_act.xml")

        base_time = datetime(2025, 1, 1)

        # INVALID file with newer date
        create_iati_file(
            resource_id=invalid_res["id"],
            namespace=namespace,
            file_type=IATIFileTypes.ACTIVITY_MAIN_FILE,
            is_valid=False,
            last_processed_success=base_time + timedelta(days=2),
        )

        # VALID file with older date
        create_iati_file(
            resource_id=valid_res["id"],
            namespace=namespace,
            file_type=IATIFileTypes.ACTIVITY_MAIN_FILE,
            is_valid=True,
            last_processed_success=base_time,
        )

        res = app.get(
            f"/iati/{namespace}/activities.xml",
            status=302,
            follow_redirects=False,
        )

        assert res.status_code == 302
        # Should choose the valid one, even though the invalid is newer
        assert res.headers["Location"] == valid_res["url"]
