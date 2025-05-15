import pytest
from unittest.mock import patch, MagicMock
from werkzeug.exceptions import HTTPException
from ckan.plugins import toolkit
from ckanext.iati_generator.blueprint.iati import iati_page


@pytest.fixture
def with_request_context():
    with toolkit.test_request_context():
        yield


class TestIatiTab:
    @patch('ckanext.iati_generator.blueprint.iati.toolkit')
    @patch('ckanext.iati_generator.blueprint.iati.render_template')
    def test_iati_page_success(self, mock_render, mock_toolkit, with_request_context):
        """
        Test that the iati_page function renders the correct template
        when the package exists and the user is logged in.
        """
        package_dict = {"id": "test-package", "name": "test-package"}
        mock_toolkit.get_action.return_value = lambda context, data_dict: package_dict

        with with_request_context:
            mock_toolkit.c = MagicMock()
            mock_toolkit.c.user = "admin"
            iati_page("test-package")

        mock_render.assert_called_with(
            "package/iati_page.html",
            pkg=package_dict,
            pkg_dict=package_dict
        )

    @patch('ckanext.iati_generator.blueprint.iati.toolkit')
    def test_iati_page_package_not_found(self, mock_toolkit, with_request_context):
        """
        Test that the iati_page function raises a 404 error
        when the package does not exist.
        """
        mock_toolkit.get_action.return_value = MagicMock(side_effect=toolkit.ObjectNotFound)
        mock_toolkit.abort.side_effect = toolkit.abort
        mock_toolkit._ = lambda x: x

        with with_request_context:
            mock_toolkit.c = MagicMock()
            mock_toolkit.c.user = "admin"
            with pytest.raises(HTTPException) as excinfo:
                iati_page("nonexistent-package")
            assert excinfo.value.code == 404
