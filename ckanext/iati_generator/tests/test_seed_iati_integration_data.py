import runpy
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def iati_script_module():
    """
    Carga el script seed_iati_integration_data.py como módulo de Python
    sin ejecutar el bloque main().
    """
    # Ruta al script: /app/src_extensions/ckanext-iati-generator/scripts/...
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "seed_iati_integration_data.py"
    assert script_path.is_file(), f"Script no encontrado en: {script_path}"

    # run_name != '__main__' para que no ejecute main()
    module_globals = runpy.run_path(str(script_path), run_name="seed_iati_integration_data")
    return module_globals


@pytest.fixture
def make_loader(iati_script_module):
    """
    Devuelve una factory para crear instancias de IATIDataLoader con el
    sample_data_config.yaml.
    """
    def _make_loader(**kwargs):
        IATIDataLoader = iati_script_module["IATIDataLoader"]

        # Directorio raíz de la extensión: .../ckanext-iati-generator
        root_dir = Path(__file__).resolve().parents[3]
        config_path = root_dir / "scripts" / "sample_data_config.yaml"
        assert config_path.is_file(), f"Config no encontrada en: {config_path}"

        return IATIDataLoader(str(config_path), **kwargs)

    return _make_loader


def test_seed_loader_world_bank_dry_run(make_loader):
    """
    Verifica que el loader cargue correctamente la org 'world-bank'
    en modo dry-run usando sample_data_config.yaml.
    """
    loader = make_loader(dry_run=True, verbose=True)

    success = loader.load_organization("world-bank")
    assert success is True

    # En sample_data_config.yaml, world-bank tiene:
    # - 1 dataset
    # - 8 resources
    # - 8 IATIFile (uno por resource)
    assert loader.stats["datasets_created"] == 1
    assert loader.stats["resources_created"] == 8
    assert loader.stats["iati_files_created"] == 8
    assert loader.stats["errors"] == []


def test_seed_loader_all_orgs_dry_run(make_loader):
    """
    Verifica que load_all() procese todas las organizaciones
    definidas en el YAML en modo dry-run.
    """
    loader = make_loader(dry_run=True, verbose=False)

    success = loader.load_all()
    assert success is True

    # En sample_data_config.yaml tenemos 2 orgs (world-bank y asian-bank),
    # cada una con 8 resources. En dry-run igual se cuentan.
    assert loader.stats["datasets_created"] == 2
    assert loader.stats["resources_created"] == 16
    assert loader.stats["iati_files_created"] == 16
    assert loader.stats["errors"] == []


def test_seed_loader_unknown_org_returns_false(make_loader):
    """
    Verifica que si se pasa una organización no definida
    en el YAML, devuelva False y registre un error.
    """
    loader = make_loader(dry_run=True)

    success = loader.load_organization("non-existing-org")
    assert success is False
    assert loader.stats["datasets_created"] == 0
    assert loader.stats["resources_created"] == 0
    assert loader.stats["iati_files_created"] == 0
    assert len(loader.stats["errors"]) == 1
    assert "Organization 'non-existing-org' not found" in loader.stats["errors"][0]
