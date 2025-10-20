import pytest
from ckan.lib.helpers import url_for
from ckan.tests import factories
from ckan import model as ckan_model

from ckanext.iati_generator.models.iati_files import IATIFile
from ckanext.iati_generator.models.enums import IATIFileTypes


# -------------------- Fixtures --------------------

@pytest.fixture(autouse=True)
def ensure_iati_files_table():
    """
    Ensures the iati_files table exists in the test database
    and cleans up after each test.
    """
    IATIFile.__table__.create(ckan_model.meta.engine, checkfirst=True)
    yield
    ckan_model.Session.query(IATIFile).delete()
    ckan_model.Session.commit()


# -------------------- Helpers --------------------

def make_iati_file(resource_dict, file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE, **kwargs):
    """
    Create an IATIFile record associated with a CKAN resource.
    """
    obj = IATIFile(
        namespace=kwargs.get("namespace", "iati-xml"),
        file_type=file_type.value if hasattr(file_type, "value") else int(file_type),
        resource_id=resource_dict["id"],
        is_valid=kwargs.get("is_valid", True),
        last_error=kwargs.get("last_error"),
    )
    obj.save()
    return obj


# -------------------- Auth tests --------------------

def test_iati_files_index_forbidden_without_user(app):
    """Ensure unauthenticated users cannot access the view."""
    url = url_for("iati_generator_admin_files.iati_files_index")
    app.get(url, status=403)


def test_iati_files_index_forbidden_for_non_admin(app):
    """Ensure non-admin users cannot access the view."""
    user = factories.UserWithToken()
    url = url_for("iati_generator_admin_files.iati_files_index")
    app.get(url, headers={"Authorization": user["token"]}, status=403)


# -------------------- Content tests --------------------

def test_iati_files_index_lists_all_iati_files_for_sysadmin(app):
    """Ensure the view lists all IATI files (resources with IATI extras)."""

    sys = factories.SysadminWithToken()

    org = factories.Organization()
    ds1 = factories.Dataset(owner_org=org["id"])
    ds2 = factories.Dataset(owner_org=org["id"])
    res1 = factories.Resource(package_id=ds1["id"], name="Res A", format="CSV")
    res2 = factories.Resource(package_id=ds2["id"], name="Res B", format="CSV")

    make_iati_file(res1, IATIFileTypes.ORGANIZATION_MAIN_FILE)
    make_iati_file(res2, IATIFileTypes.ORGANIZATION_NAMES_FILE)

    url = url_for("iati_generator_admin_files.iati_files_index")
    auth = {"Authorization": sys["token"]}
    resp = app.get(url, headers=auth)
    assert resp.status_code == 200

    # both resources appear
    assert "Res A" in resp.body
    assert "Res B" in resp.body
    # and links to their resource pages (dataset + resource_id)
    assert ds1["name"] in resp.body
    assert ds2["name"] in resp.body
    assert res1["id"] in resp.body
    assert res2["id"] in resp.body


def test_iati_files_index_shows_valid_and_error_notes(app):
    """Ensure the 'Notes' column shows the last success or error as appropriate."""
    sys = factories.SysadminWithToken()

    org = factories.Organization()
    ds = factories.Dataset(owner_org=org["id"])
    res_ok = factories.Resource(package_id=ds["id"], name="Res OK", format="CSV")
    res_bad = factories.Resource(package_id=ds["id"], name="Res BAD", format="CSV")

    # one valid (should show "Last success" when populated),
    # and one invalid with an error message
    make_iati_file(res_ok, IATIFileTypes.ORGANIZATION_MAIN_FILE, is_valid=True)
    make_iati_file(res_bad, IATIFileTypes.ORGANIZATION_NAMES_FILE, is_valid=False, last_error="Boom!")

    url = url_for("iati_generator_admin_files.iati_files_index")
    auth = {"Authorization": sys["token"]}
    resp = app.get(url, headers=auth)

    # both are present by name
    assert "Res OK" in resp.body
    assert "Res BAD" in resp.body

    # the invalid one should show the message in 'Notes'
    assert "Last error" in resp.body
    assert "Boom!" in resp.body
