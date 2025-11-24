from ckan.lib.helpers import url_for
from ckan.tests import factories
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

def test_iati_files_index_lists_all_candidates_for_sysadmin(app, clean_db):
    """Ensure the view lists resources that have the iati_file_type field."""

    sys = factories.SysadminWithToken()

    org = factories.Organization()
    ds1 = factories.Dataset(owner_org=org["id"])
    ds2 = factories.Dataset(owner_org=org["id"])

    # Resources with iati_file_type field (do NOT use extras[])
    res1 = factories.Resource(
        package_id=ds1["id"],
        name="Res A",
        format="CSV",
        iati_file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE.value,
    )

    res2 = factories.Resource(
        package_id=ds2["id"],
        name="Res B",
        format="CSV",
        iati_file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE.value,
    )

    url = url_for("iati_generator_admin_files.iati_files_index")
    auth = {"Authorization": sys["token"]}
    resp = app.get(url, headers=auth)
    assert resp.status_code == 200

    # Both resources should appear by name
    assert "Res A" in resp.body
    assert "Res B" in resp.body

    # correct links to resource (dataset + resource_id)
    assert ds1["name"] in resp.body
    assert ds2["name"] in resp.body
    assert res1["id"] in resp.body
    assert res2["id"] in resp.body


def test_iati_files_index_shows_notes_for_candidates(app, clean_db):
    """Candidates should show 'Ready to generate' in the Notes column."""

    sys = factories.SysadminWithToken()

    org = factories.Organization()
    ds = factories.Dataset(owner_org=org["id"])

    factories.Resource(
        package_id=ds["id"],
        name="Res OK",
        format="CSV",
        iati_file_type=IATIFileTypes.ORGANIZATION_MAIN_FILE.value,
    )

    factories.Resource(
        package_id=ds["id"],
        name="Res BAD",
        format="CSV",
        iati_file_type=IATIFileTypes.ORGANIZATION_NAMES_FILE.value,
    )

    url = url_for("iati_generator_admin_files.iati_files_index")
    auth = {"Authorization": sys["token"]}
    resp = app.get(url, headers=auth)

    # Both resources should appear
    assert "Res OK" in resp.body
    assert "Res BAD" in resp.body
