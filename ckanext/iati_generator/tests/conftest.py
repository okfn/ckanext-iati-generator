import contextlib

import pytest
from sqlalchemy import inspect
from ckan import model
from ckan.plugins import toolkit

from ckanext.iati_generator.models.iati_files import IATIFile


@pytest.fixture
def clean_db(reset_db, migrate_db_for):
    """Clean and initialize the database."""
    model.Session.rollback()

    # CKAN 2.10 can start the test session before the extension migration has
    # created its table.  Only perform the pre-reset cleanup when it exists.
    if inspect(model.meta.engine).has_table(IATIFile.__tablename__):
        model.Session.query(IATIFile).delete(synchronize_session=False)
        model.Session.query(model.Resource).delete(synchronize_session=False)
        model.Session.commit()

    reset_db()
    if toolkit.check_ckan_version(min_version="2.11"):
        migrate_db_for("iati_generator")
    else:
        migrate_old()


def migrate_old():
    """Apply extension migrations using the CKAN 2.10 repository API."""
    from ckan.cli.db import _resolve_alembic_config

    @contextlib.contextmanager
    def _repo_for_plugin(plugin):
        original = model.repo._alembic_ini
        model.repo._alembic_ini = _resolve_alembic_config(plugin)
        try:
            yield model.repo
        finally:
            model.repo._alembic_ini = original

    with _repo_for_plugin("iati_generator") as repo:
        repo.upgrade_db("head")
