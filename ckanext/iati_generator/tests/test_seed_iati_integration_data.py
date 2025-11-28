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
