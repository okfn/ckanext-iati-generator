import pytest
from unittest.mock import patch, MagicMock
from werkzeug.exceptions import HTTPException
from ckan.plugins import toolkit
from ckanext.iati_generator.blueprint.iati import iati_page
from ckanext.iati_generator.decorators import require_sysadmin_user


class TestIatiTab:

    @patch('ckanext.iati_generator.decorators.toolkit')
    def test_require_sysadmin_user_decorator_no_user(self, app, mock_toolkit):
        mock_toolkit.c = MagicMock()
        mock_toolkit.c.user = None
        mock_toolkit.abort.side_effect = toolkit.abort

        @require_sysadmin_user
        def test_func():
            return "Success"

        with app.test_request_context():
            with pytest.raises(HTTPException) as excinfo:
                test_func()

        assert excinfo.value.code == 403
        mock_toolkit.abort.assert_called_with(403, "Forbidden")

    @patch('ckanext.iati_generator.decorators.toolkit')
    def test_require_sysadmin_user_decorator_non_admin(self, app, mock_toolkit):
        mock_toolkit.c = MagicMock()
        mock_toolkit.c.user = "regular_user"
        mock_toolkit.c.userobj = MagicMock()
        mock_toolkit.c.userobj.sysadmin = False
        mock_toolkit.abort.side_effect = toolkit.abort

        @require_sysadmin_user
        def test_func():
            return "Success"

        with app.test_request_context():
            with pytest.raises(HTTPException) as excinfo:
                test_func()

        assert excinfo.value.code == 403
        mock_toolkit.abort.assert_called_with(403, "Sysadmin user required")

    @patch('ckanext.iati_generator.decorators.toolkit')
    def test_require_sysadmin_user_decorator_admin(self, mock_toolkit):
        mock_toolkit.c = MagicMock()
        mock_toolkit.c.user = "admin"
        mock_toolkit.c.userobj = MagicMock()
        mock_toolkit.c.userobj.sysadmin = True

        @require_sysadmin_user
        def test_func():
            return "Success"

        result = test_func()
        assert result == "Success"

    @patch('ckanext.iati_generator.blueprint.iati.toolkit')
    @patch('ckanext.iati_generator.blueprint.iati.render_template')
    def test_iati_page_success(self, mock_render, mock_toolkit, app):
        package_dict = {"id": "test-package", "name": "test-package"}
        mock_toolkit.get_action.return_value = lambda context, data_dict: package_dict
        mock_toolkit.c.user = "admin"

        with app.test_request_context():
            iati_page("test-package")

        mock_render.assert_called_with(
            "package/iati_page.html",
            pkg=package_dict,
            pkg_dict=package_dict
        )

    @patch('ckanext.iati_generator.blueprint.iati.toolkit')
    def test_iati_page_package_not_found(self, mock_toolkit, app):
        mock_toolkit.get_action.return_value = MagicMock(side_effect=toolkit.ObjectNotFound)
        mock_toolkit.c.user = "admin"
        mock_toolkit.abort.side_effect = toolkit.abort
        mock_toolkit._ = lambda x: x

        with app.test_request_context():
            with pytest.raises(HTTPException) as excinfo:
                iati_page("nonexistent-package")

        assert excinfo.value.code == 404
