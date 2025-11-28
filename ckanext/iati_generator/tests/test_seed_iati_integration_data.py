import runpy
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def iati_script_module():
    """
    Load the seed_iati_integration_data.py script as a Python module
    without executing the main() block.
    """
    # Path to script: /app/src_extensions/ckanext-iati-generator/scripts/...
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "seed_iati_integration_data.py"
    assert script_path.is_file(), f"Script not found at: {script_path}"

    # run_name != '__main__' so it doesn't execute main()
    module_globals = runpy.run_path(str(script_path), run_name="seed_iati_integration_data")
    return module_globals


@pytest.fixture
def make_loader(iati_script_module):
    """
    Returns a factory to create IATIDataLoader instances with the
    sample_data_config.yaml.
    """
    def _make_loader(**kwargs):
        IATIDataLoader = iati_script_module["IATIDataLoader"]

        # Extension root directory: .../ckanext-iati-generator
        root_dir = Path(__file__).resolve().parents[3]
        config_path = root_dir / "scripts" / "sample_data_config.yaml"
        assert config_path.is_file(), f"Config not found at: {config_path}"

        return IATIDataLoader(str(config_path), **kwargs)

    return _make_loader


def test_seed_loader_world_bank_dry_run(make_loader):
    """
    Verifies that the loader correctly loads the 'world-bank' org
    in dry-run mode using sample_data_config.yaml.
    """
    loader = make_loader(dry_run=True, verbose=True)

    success = loader.load_organization("world-bank")
    assert success is True

    # In sample_data_config.yaml, world-bank has:
    # - 1 dataset
    # - 8 resources
    # - 8 IATIFile (one per resource)
    assert loader.stats["datasets_created"] == 1
    assert loader.stats["resources_created"] == 8
    assert loader.stats["iati_files_created"] == 8
    assert loader.stats["errors"] == []


def test_seed_loader_all_orgs_dry_run(make_loader):
    """
    Verifies that load_all() processes all organizations
    defined in the YAML in dry-run mode.
    """
    loader = make_loader(dry_run=True, verbose=False)

    success = loader.load_all()
    assert success is True

    # In sample_data_config.yaml we have 2 orgs (world-bank and asian-bank),
    # each with 8 resources. In dry-run they are still counted.
    assert loader.stats["datasets_created"] == 2
    assert loader.stats["resources_created"] == 16
    assert loader.stats["iati_files_created"] == 16
    assert loader.stats["errors"] == []


def test_seed_loader_unknown_org_returns_false(make_loader):
    """
    Verifies that if an organization not defined
    in the YAML is passed, it returns False and logs an error.
    """
    loader = make_loader(dry_run=True)

    success = loader.load_organization("non-existing-org")
    assert success is False
    assert loader.stats["datasets_created"] == 0
    assert loader.stats["resources_created"] == 0
    assert loader.stats["iati_files_created"] == 0
    assert len(loader.stats["errors"]) == 1
    assert "Organization 'non-existing-org' not found" in loader.stats["errors"][0]


def test_create_or_update_dataset_dry_run_increments_stats(make_loader):
    loader = make_loader(dry_run=True)
    assert loader.stats["datasets_created"] == 0

    dataset_config = {"name": "test-dataset"}
    dataset_id = loader.create_or_update_dataset(dataset_config)

    assert dataset_id == "dummy-id-test-dataset"
    assert loader.stats["datasets_created"] == 1


def test_create_resource_with_csv_dry_run_increments_stats(make_loader):
    from io import BytesIO

    loader = make_loader(dry_run=True)
    assert loader.stats["resources_created"] == 0

    csv_file = BytesIO(b"col1,col2\n1,2")
    resource_config = {"name": "test-resource"}

    res_id = loader.create_resource_with_csv("dummy-package-id", csv_file, resource_config)

    assert res_id == "dummy-resource-test-resource"
    assert loader.stats["resources_created"] == 1


def test_create_iati_file_record_dry_run_increments_stats(make_loader):
    loader = make_loader(dry_run=True)
    assert loader.stats["iati_files_created"] == 0

    ok = loader.create_iati_file_record(
        resource_id="dummy-resource-id",
        file_type="ORGANIZATION_MAIN_FILE",
        namespace="iati-xml",
    )

    assert ok is True
    assert loader.stats["iati_files_created"] == 1


def test_download_csv_failure_records_error(make_loader, monkeypatch):
    loader = make_loader(dry_run=False)

    # Simulamos que requests.get lanza excepción
    import requests

    def fake_get(url, timeout=30):
        raise requests.exceptions.RequestException("boom")

    monkeypatch.setattr("requests.get", fake_get)

    csv = loader.download_csv_from_url("http://example.com/fail.csv")
    assert csv is None
    assert len(loader.stats["errors"]) == 1
    assert "Download failed" in loader.stats["errors"][0]


def test_load_organization_fails_if_download_fails(make_loader, monkeypatch):
    loader = make_loader(dry_run=False)

    # Forzamos que siempre falle la descarga
    monkeypatch.setattr(
        loader, "download_csv_from_url",
        lambda url: None,
    )

    success = loader.load_organization("world-bank")
    assert success is False
    # No se crean resources ni iati_files
    assert loader.stats["resources_created"] == 0
    assert loader.stats["iati_files_created"] == 0


def test_create_iati_file_record_uses_enum_and_calls_action(make_loader, monkeypatch):
    loader = make_loader(dry_run=False)

    # Evitamos pegarle a CKAN de verdad
    called = {}

    def fake_get_action(name):
        def _action(context, data_dict):
            called["name"] = name
            called["context"] = context
            called["data_dict"] = data_dict
            return {}
        return _action

    # Evitar depender de get_site_user real
    monkeypatch.setattr(loader, "_get_site_user", lambda: "test-sysadmin")
    monkeypatch.setattr("ckan.plugins.toolkit.get_action", fake_get_action)

    ok = loader.create_iati_file_record(
        resource_id="res-123",
        file_type="ORGANIZATION_MAIN_FILE",  # string → enum
        namespace="iati-xml",
    )

    assert ok is True
    assert called["name"] == "iati_file_create"
    assert called["data_dict"]["resource_id"] == "res-123"
    # Chequeo de que se haya transformado a valor numérico
    assert isinstance(called["data_dict"]["file_type"], int)
    assert called["data_dict"]["namespace"] == "iati-xml"
