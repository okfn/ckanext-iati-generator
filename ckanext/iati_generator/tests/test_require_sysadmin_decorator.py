import pytest
from unittest.mock import patch, MagicMock
from werkzeug.exceptions import HTTPException
from ckan.plugins import toolkit
from ckanext.iati_generator.decorators import require_sysadmin_user


class TestIatiTab:
    @patch('ckanext.iati_generator.decorators.toolkit')
    def test_require_sysadmin_user_decorator_no_user(self, mock_toolkit, with_request_context):
        """
        Test that the require_sysadmin_user decorator denies access
        when no user is logged in.
        """
        mock_toolkit.c = MagicMock()
        mock_toolkit.c.user = None
        mock_toolkit.abort.side_effect = toolkit.abort

        @require_sysadmin_user
        def test_func():
            return "Success"
        with pytest.raises(HTTPException) as excinfo:
            test_func()
        assert excinfo.value.code == 403
        mock_toolkit.abort.assert_called_with(403, "Forbidden")

    @patch('ckanext.iati_generator.decorators.toolkit')
    def test_require_sysadmin_user_decorator_non_admin(self, mock_toolkit, with_request_context):
        """
        Test that the require_sysadmin_user decorator denies access
        when a non-admin user is logged in.
        """
        mock_toolkit.c = MagicMock()
        mock_toolkit.c.user = "regular_user"
        mock_toolkit.c.userobj = MagicMock()
        mock_toolkit.c.userobj.sysadmin = False
        mock_toolkit.abort.side_effect = toolkit.abort

        @require_sysadmin_user
        def test_func():
            return "Success"
        with pytest.raises(HTTPException) as excinfo:
            test_func()
        assert excinfo.value.code == 403
        mock_toolkit.abort.assert_called_with(403, "Sysadmin user required")

    @patch('ckanext.iati_generator.decorators.toolkit')
    def test_require_sysadmin_user_decorator_admin(self, mock_toolkit, with_request_context):
        """
        Test that the require_sysadmin_user decorator allows access
        when a sysadmin user is logged in.
        """
        mock_toolkit.c = MagicMock()
        mock_toolkit.c.user = "admin"
        mock_toolkit.c.userobj = MagicMock()
        mock_toolkit.c.userobj.sysadmin = True

        @require_sysadmin_user
        def test_func():
            return "Success"
        result = test_func()
        assert result == "Success"
