import pytest
from types import SimpleNamespace
from pathlib import Path

from ckan.tests import factories
from ckanext.iati_generator.models.iati_files import DEFAULT_NAMESPACE
from ckanext.iati_generator.auth import iati as iati_auth
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.tests.factories import create_iati_file


@pytest.fixture
def setup_data():
    """
    Base setup:
      - sysadmin
      - org_admin (admin of the org)
      - editor
      - member
      - organization
    """
    obj = SimpleNamespace()

    # Users + tokens
    obj.org_admin = factories.UserWithToken()
    obj.org_admin["headers"] = {"Authorization": obj.org_admin["token"]}

    obj.sysadmin = factories.SysadminWithToken()
    obj.sysadmin["headers"] = {"Authorization": obj.sysadmin["token"]}

    obj.editor = factories.UserWithToken()
    obj.editor["headers"] = {"Authorization": obj.editor["token"]}

    obj.member = factories.UserWithToken()
    obj.member["headers"] = {"Authorization": obj.member["token"]}

    # Org with roles
    obj.org = factories.Organization(
        users=[
            {"name": obj.org_admin["name"], "capacity": "admin"},
            {"name": obj.editor["name"], "capacity": "editor"},
            {"name": obj.member["name"], "capacity": "member"},
        ]
    )

    # Dataset + resource are NOT strictly necessary for the action,
    # but they don't hurt if the code is expanded in the future.
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
class TestGenerateOrganizationXmlAction:
    """Tests for the generate_organization_xml action."""

    def _api(self, action):
        return f"/api/3/action/{action}"

    # -------------------------------------------------------------------------
    # Stub / monkeypatch helpers
    # -------------------------------------------------------------------------

    def _patch_successful_processing(self, monkeypatch):
        """
        Patches:
          - h.process_org_file_type => returns 1 for each type
          - IatiOrganisationMultiCsvConverter => generates minimal XML
        to avoid real calls to DB / network / external library.
        """
        # Stub for process_org_file_type (always returns 1)
        def fake_process_org_file_type(
            context,
            output_folder,
            filename,
            file_type,
            namespace,
            owner_org_id,
            required=True,
            max_files=None,
        ):
            # basic check of folder type and namespace
            assert owner_org_id
            assert isinstance(output_folder, Path)
            assert namespace  # should not be empty
            return 1

        monkeypatch.setattr(
            "ckanext.iati_generator.actions.iati.h.process_org_file_type",
            fake_process_org_file_type,
        )

        # Stub of converter that writes minimal XML
        class DummyConverter:
            def csv_folder_to_xml(self, input_folder, xml_output):
                xml_path = Path(xml_output)
                xml_path.parent.mkdir(parents=True, exist_ok=True)
                xml_path.write_text("<iati-organization/>", encoding="utf-8")
                return True

        monkeypatch.setattr(
            "ckanext.iati_generator.actions.iati.IatiOrganisationMultiCsvConverter",
            lambda: DummyConverter(),
        )

    # -------------------------------------------------------------------------
    # Success cases
    # -------------------------------------------------------------------------

    def test_generate_xml_sysadmin_ok(self, app, setup_data, monkeypatch):
        """
        Sysadmin can generate the XML and a successful result is returned.
        """
        self._patch_successful_processing(monkeypatch)

        # Necesario para la nueva lógica de auth:
        # crear el IATIFile FINAL_ORGANIZATION_FILE para este namespace.
        create_iati_file(
            resource_id=setup_data.res["id"],
            namespace="bcie-namespace",
            file_type=IATIFileTypes.FINAL_ORGANIZATION_FILE.value,
        )

        payload = {
            "namespace": "bcie-namespace",
        }

        res = app.post(
            self._api("generate_organization_xml"),
            params=payload,
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]

        assert res["success"] is True
        assert res["message"] == "Organization XML generated and uploaded successfully"
        # In the real code 5 organization file types are processed
        # (MAIN, NAMES, BUDGET, EXPENDITURE, DOCUMENT), so 5 * 1 = 5
        assert res["files_processed"] == 5

    def test_generate_xml_org_admin_ok(self, app, setup_data, monkeypatch):
        """
        Org admin can generate the XML for their organization.
        """
        self._patch_successful_processing(monkeypatch)

        # Para el caso sin 'namespace', se usa DEFAULT_NAMESPACE
        create_iati_file(
            resource_id=setup_data.res["id"],
            namespace=DEFAULT_NAMESPACE,
            file_type=IATIFileTypes.FINAL_ORGANIZATION_FILE.value,
        )

        payload = {
            # let it use DEFAULT_NAMESPACE to test that case
        }

        res = app.post(
            self._api("generate_organization_xml"),
            params=payload,
            headers=setup_data.org_admin["headers"],
            status=200,
        ).json["result"]

        assert res["success"] is True
        assert res["files_processed"] == 5

    def test_generate_xml_uses_default_namespace(self, app, setup_data, monkeypatch):
        """
        If namespace is not passed, the function should use DEFAULT_NAMESPACE.
        We verify this by inspecting the stub.
        """
        calls = []

        # Crear el FINAL_ORGANIZATION_FILE para DEFAULT_NAMESPACE
        create_iati_file(
            resource_id=setup_data.res["id"],
            namespace=DEFAULT_NAMESPACE,
            file_type=IATIFileTypes.FINAL_ORGANIZATION_FILE.value,
        )

        def fake_process_org_file_type(
            context,
            output_folder,
            filename, file_type,
            namespace,
            owner_org_id,
            required=True,
            max_files=None,
        ):
            calls.append(namespace)
            return 1

        monkeypatch.setattr(
            "ckanext.iati_generator.actions.iati.h.process_org_file_type",
            fake_process_org_file_type,
        )

        class DummyConverter:
            def csv_folder_to_xml(self, input_folder, xml_output):
                xml_path = Path(xml_output)
                xml_path.parent.mkdir(parents=True, exist_ok=True)
                xml_path.write_text("<iati-organization/>", encoding="utf-8")
                return True

        monkeypatch.setattr(
            "ckanext.iati_generator.actions.iati.IatiOrganisationMultiCsvConverter",
            lambda: DummyConverter(),
        )

        payload = {
            # WITHOUT namespace
        }

        res = app.post(
            self._api("generate_organization_xml"),
            params=payload,
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]

        assert res["success"] is True
        assert res["files_processed"] == 5
        # All calls should have used DEFAULT_NAMESPACE
        assert calls
        assert all(ns == DEFAULT_NAMESPACE for ns in calls)

    # -------------------------------------------------------------------------
    # Permission / auth errors
    # -------------------------------------------------------------------------

    def test_generate_xml_denied_for_editor_and_member(self, app, setup_data):
        """
        Editor and member CANNOT generate the XML.
        """
        payload = {
            "namespace": DEFAULT_NAMESPACE,
        }

        # editor -> 403
        app.post(
            self._api("generate_organization_xml"),
            params=payload,
            headers=setup_data.editor["headers"],
            status=403,
        )

        # member -> 403
        app.post(
            self._api("generate_organization_xml"),
            params=payload,
            headers=setup_data.member["headers"],
            status=403,
        )

    def test_generate_xml_denied_when_admin_of_other_org(self, app, setup_data):
        """
        An admin of another organization CANNOT generate XML for this org.
        """
        # Crear otra org + dataset + resource
        other_org = factories.Organization()
        other_pkg = factories.Dataset(owner_org=other_org["id"])
        other_res = factories.Resource(package_id=other_pkg["id"])

        # Y el FINAL_ORGANIZATION_FILE está asociado a esa otra org
        create_iati_file(
            resource_id=other_res["id"],
            namespace=DEFAULT_NAMESPACE,
            file_type=IATIFileTypes.FINAL_ORGANIZATION_FILE.value,
        )

        payload = {
            "namespace": DEFAULT_NAMESPACE,
        }

        app.post(
            self._api("generate_organization_xml"),
            params=payload,
            headers=setup_data.org_admin["headers"],
            status=403,
        )

    def test_generate_xml_missing_final_org_file(self):
        """
        If there is no FINAL_ORGANIZATION_FILE for the namespace,
        the auth function generate_organization_xml returns success=False
        and the appropriate error message.
        """
        context = {}
        data_dict = {
            "namespace": DEFAULT_NAMESPACE,
        }

        auth_result = iati_auth.generate_organization_xml(context, data_dict)

        assert auth_result["success"] is False
        assert "FINAL_ORGANIZATION_FILE" in auth_result["msg"]

    # -------------------------------------------------------------------------
    # Internal flow errors
    # -------------------------------------------------------------------------

    def test_generate_xml_failed_conversion_returns_error(self, app, setup_data, monkeypatch):
        """
        If the converter does not generate the XML or returns False,
        the action should return success=False and the corresponding message.
        """
        # Force the file download to report success (5 files)
        monkeypatch.setattr(
            "ckanext.iati_generator.actions.iati._process_org_csv_files",
            lambda *args, **kwargs: 5
        )

        # Force the XML conversion to fail (returns None)
        # This will bypass the real converter logic and trigger the error in the action
        monkeypatch.setattr(
            "ckanext.iati_generator.actions.iati._convert_org_xml",
            lambda *args, **kwargs: None
        )

        # Create the necessary record to pass the auth and start the action
        create_iati_file(
            resource_id=setup_data.res["id"],
            namespace=DEFAULT_NAMESPACE,
            file_type=IATIFileTypes.FINAL_ORGANIZATION_FILE.value,
        )

        # Execute
        res = app.post(
            self._api("generate_organization_xml"),
            params={"namespace": DEFAULT_NAMESPACE},
            headers=setup_data.sysadmin["headers"],
            status=200,
        ).json["result"]

        # Verify the error message from the action
        assert res["success"] is False
        # Note: The message "No organization CSV files found..." is what your action returns
        # when _convert_org_xml returns None.
        # We will validate that the message contains the key part.
        assert "No organization CSV files found" in res["message"]
