import pytest

from ckan.plugins import toolkit

from ckanext.iati_generator.actions.procces import (
    upload_or_update_xml_resource,
)
from ckanext.iati_generator.models.enums import IATIFileTypes


@pytest.mark.parametrize("invalid_file_type", ["", None, "invalid"])
def test_upload_ignores_resource_with_invalid_iati_file_type(
    monkeypatch,
    tmp_path,
    invalid_file_type,
):
    """Resources without a valid IATI type must not block XML creation."""
    xml_path = tmp_path / "activity.xml"
    xml_path.write_bytes(b"<iati-activities />")

    dataset = {
        "id": "dataset-id",
        "resources": [
            {
                "id": "invalid-resource-id",
                "iati_file_type": invalid_file_type,
            },
            {
                "id": "activities-csv-id",
                "iati_file_type": str(
                    IATIFileTypes.ACTIVITY_MAIN_FILE.value
                ),
            },
        ],
    }
    captured = {}

    def resource_create(context, data_dict):
        captured["context"] = context
        captured["data_dict"] = data_dict
        return {
            "id": "new-activity-xml-id",
            "package_id": data_dict["package_id"],
        }

    def get_action(action_name):
        assert action_name == "resource_create"
        return resource_create

    monkeypatch.setattr(toolkit, "get_action", get_action)

    result = upload_or_update_xml_resource(
        {"user": "test-user"},
        dataset,
        str(xml_path),
        "activity.xml",
        IATIFileTypes.FINAL_ACTIVITY_FILE,
    )

    assert result["id"] == "new-activity-xml-id"
    assert captured["data_dict"]["package_id"] == "dataset-id"
    assert captured["data_dict"]["name"] == "activity.xml"
    assert captured["data_dict"]["format"] == "XML"
    assert (
        captured["data_dict"]["iati_file_type"]
        == IATIFileTypes.FINAL_ACTIVITY_FILE.value
    )


def test_upload_updates_existing_activity_xml_resource(
    monkeypatch,
    tmp_path,
):
    """An existing final activity resource must be patched, not recreated."""
    xml_path = tmp_path / "activity.xml"
    xml_path.write_bytes(b"<iati-activities />")

    dataset = {
        "id": "dataset-id",
        "resources": [
            {
                "id": "empty-resource-id",
                "iati_file_type": "",
            },
            {
                "id": "existing-activity-xml-id",
                "iati_file_type": str(
                    IATIFileTypes.FINAL_ACTIVITY_FILE.value
                ),
            },
        ],
    }
    captured = {}

    def resource_patch(context, data_dict):
        captured["context"] = context
        captured["data_dict"] = data_dict
        return {
            "id": data_dict["id"],
            "package_id": dataset["id"],
        }

    def get_action(action_name):
        assert action_name == "resource_patch"
        return resource_patch

    monkeypatch.setattr(toolkit, "get_action", get_action)

    result = upload_or_update_xml_resource(
        {"user": "test-user"},
        dataset,
        str(xml_path),
        "activity.xml",
        IATIFileTypes.FINAL_ACTIVITY_FILE,
    )

    assert result["id"] == "existing-activity-xml-id"
    assert captured["data_dict"]["id"] == "existing-activity-xml-id"
    assert "package_id" not in captured["data_dict"]
    assert captured["data_dict"]["name"] == "activity.xml"
    assert captured["data_dict"]["format"] == "XML"
    assert (
        captured["data_dict"]["iati_file_type"]
        == IATIFileTypes.FINAL_ACTIVITY_FILE.value
    )
