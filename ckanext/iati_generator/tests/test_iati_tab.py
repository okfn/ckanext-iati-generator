from ckan.tests import factories


class TestIatiTab:

    def test_serve_iati_file_not_found(self, app):
        """
        Test that serve_iati_file returns 404 if file is missing.
        """
        user = factories.SysadminWithToken()
        resource_id = "abc123456789"
        fake_filename = "missing_file.xml"
        url = f"/iati-dataset/static-iati/{resource_id}/{fake_filename}"
        auth = {"Authorization": user["token"]}
        response = app.get(url, headers=auth, status=404)
        assert "XML file not found" in response.body
