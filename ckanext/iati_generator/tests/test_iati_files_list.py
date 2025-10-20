from ckan.lib.helpers import url_for
from ckan.tests import factories

from ckanext.iati_generator.tests.factories import create_iati_file
from ckanext.iati_generator.models.enums import IATIFileTypes


# -------------------- Auth tests --------------------

def test_iati_files_index_forbidden_without_user(app, clean_db):
    """Ensure unauthenticated users cannot access the view."""
    url = url_for("iati_generator_admin_files.iati_files_index")
    app.get(url, status=403)


def test_iati_files_index_forbidden_for_non_admin(app, clean_db):
    """Ensure non-admin users cannot access the view."""
    user = factories.UserWithToken()
    url = url_for("iati_generator_admin_files.iati_files_index")
    app.get(url, headers={"Authorization": user["token"]}, status=403)


# -------------------- Content tests --------------------

def test_iati_files_index_lists_all_iati_files_for_sysadmin(app, clean_db):
    """Ensure the view lists all IATI files (resources with IATI extras)."""

    sys = factories.SysadminWithToken()

    org = factories.Organization()
    ds1 = factories.Dataset(owner_org=org["id"])
    ds2 = factories.Dataset(owner_org=org["id"])
    res1 = factories.Resource(package_id=ds1["id"], name="Res A", format="CSV")
    res2 = factories.Resource(package_id=ds2["id"], name="Res B", format="CSV")

    create_iati_file(resource_id=res1["id"], file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE)
    create_iati_file(resource_id=res2["id"], file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE)

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


def test_iati_files_index_shows_valid_and_error_notes(app, clean_db):
    """Ensure the 'Notes' column shows the last success or error as appropriate."""
    sys = factories.SysadminWithToken()

    org = factories.Organization()
    ds = factories.Dataset(owner_org=org["id"])
    res_ok = factories.Resource(package_id=ds["id"], name="Res OK", format="CSV")
    res_bad = factories.Resource(package_id=ds["id"], name="Res BAD", format="CSV")

    # one valid (should show "Last success" when populated),
    # and one invalid with an error message
    create_iati_file(resource_id=res_ok["id"], file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE, is_valid=True)
    create_iati_file(resource_id=res_bad["id"],
                     file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE, is_valid=False, last_error="Boom!")

    url = url_for("iati_generator_admin_files.iati_files_index")
    auth = {"Authorization": sys["token"]}
    resp = app.get(url, headers=auth)

    # both are present by name
    assert "Res OK" in resp.body
    assert "Res BAD" in resp.body

    # the invalid one should show the message in 'Notes'
    assert "Last error" in resp.body
    assert "Boom!" in resp.body
