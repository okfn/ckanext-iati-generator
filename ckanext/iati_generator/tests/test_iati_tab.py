import pytest
from flask import Flask
from unittest.mock import patch, MagicMock
from werkzeug.exceptions import HTTPException
from ckan.plugins import toolkit
from ckanext.iati_generator.blueprint.iati import iati_page


@pytest.fixture
def with_request_context():
    app = Flask(__name__)
    app.secret_key = "test-secret-key"
    with app.test_request_context():
        yield


class TestIatiTab:

    @patch('ckanext.iati_generator.blueprint.iati.toolkit.check_access')
    @patch('ckanext.iati_generator.blueprint.iati.render_template')
    def test_iati_page_success(self, mock_render, mock_check_access, with_request_context):
        """
        Test that the iati_page function renders the correct template
        when the package exists and the user is logged in.
        """
        package_dict = {"id": "test-package", "name": "test-package"}
        mock_check_access.return_value = None

        # Simular contexto del usuario admin
        toolkit.c = MagicMock()
        toolkit.c.user = "admin"

        # Simular get_action
        with patch('ckanext.iati_generator.blueprint.iati.toolkit.get_action') as mock_get_action:
            mock_get_action.return_value = lambda context, data_dict: package_dict
            iati_page("test-package")

        mock_render.assert_called_with(
            "package/iati_page.html",
            pkg=package_dict,
            pkg_dict=package_dict
        )

    @patch('ckanext.iati_generator.blueprint.iati.toolkit.check_access')
    def test_iati_page_package_not_found(self, mock_check_access, with_request_context):
        """
        Test that the iati_page function raises a 404 error
        when the package does not exist.
        """
        mock_check_access.return_value = None
        toolkit.c = MagicMock()
        toolkit.c.user = "admin"

        with patch('ckanext.iati_generator.blueprint.iati.toolkit.get_action') as mock_get_action, \
            patch('ckanext.iati_generator.blueprint.iati.toolkit.abort', side_effect=toolkit.abort), \
                patch('ckanext.iati_generator.blueprint.iati.toolkit._', lambda x: x):

            mock_get_action.side_effect = toolkit.ObjectNotFound

            with pytest.raises(HTTPException) as excinfo:
                iati_page("nonexistent-package")
            assert excinfo.value.code == 404
