import pytest

from ckan.plugins import toolkit
from ckan.tests import factories

from ckanext.iati_generator.actions.procces import (
    upload_or_update_xml_resource,
)
from ckanext.iati_generator.models.enums import IATIFileTypes
from ckanext.iati_generator.tests.factories import IATIResource

pytestmark = pytest.mark.usefixtures("with_plugins", "clean_db")


def test_upload_creates_new_activity_xml_resource_when_missing(tmp_path):
    """If no XML resource exists, a new final activity resource is created."""
    sysadmin = factories.SysadminWithToken()
    user_context = {"user": sysadmin["name"]}

    dataset = factories.Dataset()
    IATIResource(
        package_id=dataset["id"],
        name="problematic.csv",
        iati_file_type="",
    )
    dataset = toolkit.get_action("package_show")(
        user_context,
        {"id": dataset["id"]},
    )

    xml_path = tmp_path / "activity.xml"
    xml_path.write_bytes(b"<iati-activities />")

    result = upload_or_update_xml_resource(
        user_context,
        dataset,
        str(xml_path),
        "activity.xml",
        IATIFileTypes.FINAL_ACTIVITY_FILE,
    )

    refreshed_dataset = toolkit.get_action("package_show")(
        user_context,
        {"id": dataset["id"]},
    )

    assert result["id"]
    assert len(refreshed_dataset["resources"]) == 2
    assert any(
        resource["name"] == "activity.xml"
        and resource["iati_file_type"]
        == IATIFileTypes.FINAL_ACTIVITY_FILE.value
        for resource in refreshed_dataset["resources"]
    )


def test_upload_updates_existing_activity_xml_resource_without_increasing_count(
    tmp_path,
):
    """If the XML resource already exists, it is patched in place."""
    sysadmin = factories.SysadminWithToken()
    user_context = {"user": sysadmin["name"]}

    dataset = factories.Dataset()
    IATIResource(
        package_id=dataset["id"],
        name="problematic.csv",
        iati_file_type="",
    )
    existing = IATIResource(
        package_id=dataset["id"],
        name="activity.xml",
        url_type="upload",
    )
    dataset = toolkit.get_action("package_show")(
        user_context,
        {"id": dataset["id"]},
    )

    xml_path = tmp_path / "activity.xml"
    xml_path.write_bytes(b"<iati-activities />")

    result = upload_or_update_xml_resource(
        user_context,
        dataset,
        str(xml_path),
        "activity.xml",
        IATIFileTypes.FINAL_ACTIVITY_FILE,
    )

    refreshed_dataset = toolkit.get_action("package_show")(
        user_context,
        {"id": dataset["id"]},
    )

    assert result["id"] == existing["id"]
    assert len(refreshed_dataset["resources"]) == 2
    assert sum(
        resource["name"] == "activity.xml"
        and resource["iati_file_type"]
        == IATIFileTypes.FINAL_ACTIVITY_FILE.value
        for resource in refreshed_dataset["resources"]
    ) == 1
