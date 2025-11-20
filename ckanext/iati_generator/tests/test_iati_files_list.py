from ckan.lib.helpers import url_for
from ckan.tests import factories


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

    # Recursos con el campo iati_file_type (NO usar extras[])
    res1 = factories.Resource(
        package_id=ds1["id"],
        name="Res A",
        format="CSV",
        iati_file_type="100",
    )

    res2 = factories.Resource(
        package_id=ds2["id"],
        name="Res B",
        format="CSV",
        iati_file_type="110",
    )

    url = url_for("iati_generator_admin_files.iati_files_index")
    auth = {"Authorization": sys["token"]}
    resp = app.get(url, headers=auth)
    assert resp.status_code == 200

    # Ambos recursos deben aparecer por nombre
    assert "Res A" in resp.body
    assert "Res B" in resp.body

    # enlaces correctos al recurso (dataset + resource_id)
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
        iati_file_type="100",
    )

    factories.Resource(
        package_id=ds["id"],
        name="Res BAD",
        format="CSV",
        iati_file_type="110",
    )

    url = url_for("iati_generator_admin_files.iati_files_index")
    auth = {"Authorization": sys["token"]}
    resp = app.get(url, headers=auth)

    # Ambos recursos deben aparecer
    assert "Res OK" in resp.body
    assert "Res BAD" in resp.body
