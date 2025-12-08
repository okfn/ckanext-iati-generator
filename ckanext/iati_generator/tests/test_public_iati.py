from datetime import datetime, timedelta

import pytest
from ckan.tests import factories

from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.tests.factories import create_iati_file


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPublicIatiEndpoints:
    def test_org_redirects_to_latest_valid_file(self, app):
        """
        /iati/<namespace>/organization.xml debe redirigir al recurso
        más reciente (last_processed_success) y válido (is_valid=True).
        """
        namespace = "test-namespace-org"

        # Creamos dos recursos con URLs distintas
        older_res = factories.Resource(url="http://example.org/old_org.xml")
        newer_res = factories.Resource(url="http://example.org/new_org.xml")

        base_time = datetime(2025, 1, 1)

        # IATIFile más viejo
        create_iati_file(
            resource_id=older_res["id"],
            namespace=namespace,
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
            is_valid=True,
            last_processed_success=base_time,
        )

        # IATIFile más nuevo
        create_iati_file(
            resource_id=newer_res["id"],
            namespace=namespace,
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
            is_valid=True,
            last_processed_success=base_time + timedelta(days=1),
        )

        # Llamamos al endpoint público (sin autenticación)
        res = app.get(
            f"/iati/{namespace}/organization.xml",
            status=302,
            follow_redirects=False,
        )
        assert res.status_code == 302
        # Debe redirigir al recurso más nuevo
        assert res.headers["Location"] == newer_res["url"]

    def test_org_ignores_invalid_files(self, app):
        """
        Debe ignorar registros con is_valid=False.
        """
        namespace = "test-namespace-org-invalid"

        invalid_res = factories.Resource(url="http://example.org/invalid_org.xml")
        valid_res = factories.Resource(url="http://example.org/valid_org.xml")

        base_time = datetime(2025, 1, 1)

        # Archivo INVALIDO con fecha más nueva
        create_iati_file(
            resource_id=invalid_res["id"],
            namespace=namespace,
            file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE,
            is_valid=False,
            last_processed_success=base_time + timedelta(days=2),
        )

        # Archivo VALIDO con fecha más vieja
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
        # Debe elegir el válido, aunque el inválido sea más nuevo
        assert res.headers["Location"] == valid_res["url"]

    def test_org_returns_404_when_no_files(self, app):
        """
        Si no hay ningún IATIFile para ese namespace+tipo, debe dar 404.
        """
        namespace = "no-such-namespace"
        res = app.get(f"/iati/{namespace}/organization.xml", status=404)
        assert "No organization XML" in res.text

    def test_activities_redirects_to_latest_valid_file(self, app):
        """
        /iati/<namespace>/activities.xml debe redirigir al último
        IATIFile válido del tipo ACTIVITY_MAIN_FILE.
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
        Docstring for test_activities_returns_404_when_no_files

        :param self: Description
        :param app: Description
        """
        namespace = "no-such-namespace-act"
        res = app.get(
            f"/iati/{namespace}/activities.xml",
            status=404,
        )
        assert "No activities XML" in res.text
