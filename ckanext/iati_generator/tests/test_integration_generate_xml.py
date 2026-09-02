"""End-to-end test: CSV resources -> IATI XML -> back to CSV.

Reproduces what an organisation admin does in the portal:

1. upload one CSV resource per IATI file type (``iati_file_type`` extra),
2. trigger ``iati_generate_activities_xml`` / ``iati_generate_organisation_xml``,
3. get a valid IATI 2.03 XML published as a resource of the same dataset and
   resolvable through the public ``/iati/<namespace>/*.xml`` endpoints.

The generated activity XML is validated against the IATI 2.03 schema and
ruleset and converted back to CSV with okfn_iati, and the recovered
``locations.csv`` must be identical to the uploaded one (all 20 columns, one
pair of rows per way of expressing a location: ISO country, administrative
area, exact point, approximate point, name only, gazetteer id).

Fixture CSVs live in ``tests/fixtures/iati_csv``; ``locations.csv`` is the
same file used as example in the BCIE documentation and in okfn_iati's own
``tests/sample_locations.csv``.
"""
import csv
import io
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import pytest
from lxml import etree
import okfn_iati
from okfn_iati import IatiMultiCsvConverter
from okfn_iati.iati_schema_validator import IatiValidator
from ckan.tests import factories

from ckanext.iati_generator.models.enums import IATIFileTypes

FIXTURES = Path(__file__).parent / "fixtures" / "iati_csv"
NAMESPACE = "xm-dac-46008-test"
ACTIVITY_ID = "XM-DAC-46008-cfa012402"

ACTIVITY_FILES = {
    "activities.csv": IATIFileTypes.ACTIVITY_MAIN_FILE,
    "participating_orgs.csv": IATIFileTypes.ACTIVITY_PARTICIPATING_ORGS_FILE,
    "sectors.csv": IATIFileTypes.ACTIVITY_SECTORS_FILE,
    "locations.csv": IATIFileTypes.ACTIVITY_LOCATIONS_FILE,
}
ORGANISATION_FILES = {
    "organisations.csv": IATIFileTypes.ORGANIZATION_MAIN_FILE,
    "names.csv": IATIFileTypes.ORGANIZATION_NAMES_FILE,
}


def _api(action):
    return f"/api/3/action/{action}"


def read_rows(path):
    with Path(path).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def upload_csv(app, headers, package_id, filename, file_type, content=None):
    """Create a CSV resource with an uploaded file, as the UI does."""
    if content is None:
        content = (FIXTURES / filename).read_bytes()
    resp = app.post(
        _api("resource_create"),
        data={
            "package_id": package_id,
            "name": filename,
            "format": "CSV",
            "iati_file_type": str(file_type.value),
            "upload": (io.BytesIO(content), filename),
        },
        headers=headers,
        status=200,
    )
    return resp.json["result"]


def download(app, headers, url):
    """Fetch a resource download URL through the test app and return its bytes."""
    resp = app.get(urlparse(url).path, headers=headers, status=200)
    return resp.data


def resources_of_type(app, headers, package_id, file_type):
    pkg = app.get(_api("package_show"), params={"id": package_id}, headers=headers, status=200).json["result"]
    return [r for r in pkg["resources"] if str(r.get("iati_file_type", "")) == str(file_type.value)]


@pytest.fixture
def env():
    """Org admin + editor, an organisation and an IATI dataset owned by it."""
    obj = SimpleNamespace()
    obj.org_admin = factories.UserWithToken()
    obj.org_admin["headers"] = {"Authorization": obj.org_admin["token"]}
    obj.editor = factories.UserWithToken()
    obj.editor["headers"] = {"Authorization": obj.editor["token"]}
    obj.org = factories.Organization(users=[
        {"name": obj.org_admin["name"], "capacity": "admin"},
        {"name": obj.editor["name"], "capacity": "editor"},
    ])
    obj.pkg = factories.Dataset(
        owner_org=obj.org["id"],
        extras=[{"key": "iati_namespace", "value": NAMESPACE}],
    )
    return obj


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestGenerateActivitiesXmlEndToEnd:

    def _upload_all(self, app, env, files=ACTIVITY_FILES):
        return {
            name: upload_csv(app, env.org_admin["headers"], env.pkg["id"], name, ftype)
            for name, ftype in files.items()
        }

    def test_csv_resources_to_valid_xml_and_back_to_csv(self, app, env, tmp_path):
        uploaded = self._upload_all(app, env)
        for name, res in uploaded.items():
            assert res["format"] == "CSV"
            assert str(res["iati_file_type"]) == str(ACTIVITY_FILES[name].value)

        # --- generate -----------------------------------------------------
        result = app.post(
            _api("iati_generate_activities_xml"),
            params={"package_id": env.pkg["id"]},
            headers=env.org_admin["headers"],
            status=200,
        ).json["result"]

        assert result["name"] == "activity.xml"
        assert result["format"] == "XML"
        assert int(result["iati_file_type"]) == IATIFileTypes.FINAL_ACTIVITY_FILE.value
        assert result["package_id"] == env.pkg["id"]
        finals = resources_of_type(app, env.org_admin["headers"], env.pkg["id"], IATIFileTypes.FINAL_ACTIVITY_FILE)
        assert [r["id"] for r in finals] == [result["id"]]

        # --- the XML is a valid IATI 2.03 activity file -------------------
        xml_bytes = download(app, env.org_admin["headers"], result["url"])
        xml_text = xml_bytes.decode("utf-8")
        valid, errors = IatiValidator().validate(xml_text)
        assert valid, json.dumps(errors, indent=1)

        root = ET.fromstring(xml_bytes)
        assert root.tag == "iati-activities"
        assert root.get("version") == "2.03"
        activities = root.findall("iati-activity")
        assert [a.findtext("iati-identifier") for a in activities] == [ACTIVITY_ID]
        activity = activities[0]
        assert activity.find("reporting-org").get("ref") == "XM-DAC-46008"
        assert len(activity.findall("participating-org")) == 1
        assert activity.find("sector").get("code") == "14030"

        # Locations are emitted with the IATI 2.03 child elements
        locations = {loc.get("ref"): loc for loc in activity.findall("location")}
        assert len(locations) == 12
        country = locations["LOC-PAIS-HN"]
        assert country.find("location-id").attrib == {"vocabulary": "A4", "code": "HN"}
        assert country.find("location-reach").get("code") == "1"
        assert country.find("exactness").get("code") == "1"
        assert country.find("location-class").get("code") == "1"
        assert country.find("feature-designation").get("code") == "PCLI"
        point = locations["LOC-PT-HOSP"]
        assert point.find("point/pos").text == "14.0891 -87.1650"
        assert point.find("administrative").attrib == {"vocabulary": "G1", "code": "3608992", "level": "1"}
        assert locations["LOC-REG-CS"].find("location-reach").get("code") == "2"
        assert locations["LOC-OSM-PC"].find("location-id").get("code") == "relation/1234567"

        # --- and it converts back to the CSVs that were uploaded ----------
        xml_path = tmp_path / "activity.xml"
        xml_path.write_bytes(xml_bytes)
        csv_folder = tmp_path / "csv"
        assert IatiMultiCsvConverter().xml_to_csv_folder(str(xml_path), str(csv_folder))

        expected = {r["location_ref"]: r for r in read_rows(FIXTURES / "locations.csv")}
        recovered = {r["location_ref"]: r for r in read_rows(csv_folder / "locations.csv")}
        assert set(recovered) == set(expected)
        columns = IatiMultiCsvConverter.csv_files["locations"]["columns"]
        for ref, row in expected.items():
            for col in columns:
                assert recovered[ref].get(col, "") == row[col], f"{ref}.{col}"

        activities_back = read_rows(csv_folder / "activities.csv")
        activities_in = read_rows(FIXTURES / "activities.csv")
        assert len(activities_back) == len(activities_in) == 1
        for col in ("activity_identifier", "title", "activity_status", "default_currency",
                    "reporting_org_ref", "recipient_country_code"):
            assert activities_back[0][col] == activities_in[0][col], col
        # okfn_iati writes every <activity-date> to activity_date.csv on the way back
        dates = read_rows(csv_folder / "activity_date.csv")
        assert [(d["type"], d["iso_date"]) for d in dates] == [("1", activities_in[0]["planned_start_date"])]
        assert len(read_rows(csv_folder / "sectors.csv")) == len(read_rows(FIXTURES / "sectors.csv"))
        assert len(read_rows(csv_folder / "participating_orgs.csv")) == len(read_rows(FIXTURES / "participating_orgs.csv"))

        # --- published through the public namespace endpoint --------------
        resp = app.get(f"/iati/{NAMESPACE}/activity.xml", status=302, follow_redirects=False)
        assert resp.headers["Location"] == result["url"]

    def test_regenerating_patches_the_same_xml_resource(self, app, env):
        self._upload_all(app, env)
        first = app.post(_api("iati_generate_activities_xml"), params={"package_id": env.pkg["id"]},
                         headers=env.org_admin["headers"], status=200).json["result"]
        second = app.post(_api("iati_generate_activities_xml"), params={"package_id": env.pkg["id"]},
                          headers=env.org_admin["headers"], status=200).json["result"]
        assert first["id"] == second["id"]
        finals = resources_of_type(app, env.org_admin["headers"], env.pkg["id"], IATIFileTypes.FINAL_ACTIVITY_FILE)
        assert len(finals) == 1

    def test_generate_through_admin_page_redirects_to_iati_files_index(self, app, env):
        self._upload_all(app, env)
        resp = app.post(
            f"/generate-iati-activity_file/{env.pkg['id']}",
            headers=env.org_admin["headers"],
            status=302,
            follow_redirects=False,
        )
        assert resp.headers["Location"].endswith(f"/dataset/iati-files/{env.pkg['id']}")
        finals = resources_of_type(app, env.org_admin["headers"], env.pkg["id"], IATIFileTypes.FINAL_ACTIVITY_FILE)
        assert len(finals) == 1

    def test_invalid_locations_csv_blocks_generation(self, app, env):
        """The okfn_iati CSV validators run before the converter: bad codes are reported per file."""
        files = {k: v for k, v in ACTIVITY_FILES.items() if k != "locations.csv"}
        self._upload_all(app, env, files)
        rows = read_rows(FIXTURES / "locations.csv")
        rows[0]["exactness"] = "3"      # GeographicExactness only allows 1 or 2
        rows[1]["latitude"] = "14.0"    # latitude without longitude
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        upload_csv(app, env.org_admin["headers"], env.pkg["id"], "locations.csv",
                   IATIFileTypes.ACTIVITY_LOCATIONS_FILE, buf.getvalue().encode("utf-8"))

        resp = app.post(_api("iati_generate_activities_xml"), params={"package_id": env.pkg["id"]},
                        headers=env.org_admin["headers"], status=409)
        error = json.dumps(resp.json["error"])
        assert "locations.csv" in error
        assert "exactness" in error
        assert "longitude" in error
        assert resources_of_type(app, env.org_admin["headers"], env.pkg["id"], IATIFileTypes.FINAL_ACTIVITY_FILE) == []

    def test_missing_activities_csv_blocks_generation(self, app, env):
        upload_csv(app, env.org_admin["headers"], env.pkg["id"], "locations.csv", IATIFileTypes.ACTIVITY_LOCATIONS_FILE)
        resp = app.post(_api("iati_generate_activities_xml"), params={"package_id": env.pkg["id"]},
                        headers=env.org_admin["headers"], status=409)
        assert "activities.csv" in json.dumps(resp.json["error"])

    def test_editor_cannot_generate(self, app, env):
        self._upload_all(app, env)
        app.post(_api("iati_generate_activities_xml"), params={"package_id": env.pkg["id"]},
                 headers=env.editor["headers"], status=403)


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestGenerateOrganisationXmlEndToEnd:

    def test_csv_resources_to_valid_organisation_xml(self, app, env):
        for name, ftype in ORGANISATION_FILES.items():
            upload_csv(app, env.org_admin["headers"], env.pkg["id"], name, ftype)

        result = app.post(
            _api("iati_generate_organisation_xml"),
            params={"package_id": env.pkg["id"]},
            headers=env.org_admin["headers"],
            status=200,
        ).json["result"]
        assert result["name"] == "organisation.xml"
        assert result["format"] == "XML"
        assert int(result["iati_file_type"]) == IATIFileTypes.FINAL_ORGANIZATION_FILE.value

        xml_bytes = download(app, env.org_admin["headers"], result["url"])
        schema_dir = Path(okfn_iati.__file__).parent / "schemas" / "2.03"
        schema = etree.XMLSchema(etree.parse(str(schema_dir / "iati-organisations-schema.xsd")))
        doc = etree.fromstring(xml_bytes)
        assert schema.validate(doc), schema.error_log

        orgs = doc.findall("iati-organisation")
        assert len(orgs) == 1
        assert orgs[0].findtext("organisation-identifier") == "XM-DAC-46008"
        names = {n.get("{http://www.w3.org/XML/1998/namespace}lang"): n.text
                 for n in orgs[0].findall("name/narrative")}
        assert names.get("en") == "Central American Bank for Economic Integration"

        resp = app.get(f"/iati/{NAMESPACE}/organisation.xml", status=302, follow_redirects=False)
        assert resp.headers["Location"] == result["url"]

    def test_missing_organisations_csv_blocks_generation(self, app, env):
        upload_csv(app, env.org_admin["headers"], env.pkg["id"], "names.csv", IATIFileTypes.ORGANIZATION_NAMES_FILE)
        resp = app.post(_api("iati_generate_organisation_xml"), params={"package_id": env.pkg["id"]},
                        headers=env.org_admin["headers"], status=409)
        assert "organisations.csv" in json.dumps(resp.json["error"])
