import pytest
from sqlalchemy import inspect
from ckan import model

from ckanext.iati_generator.models.iati_files import IATIFile


@pytest.fixture
def clean_db(reset_db, migrate_db_for):
    """Clean and initialize the database."""
    model.Session.rollback()

    # The extension table does not exist before its migration runs on a fresh
    # test database. Clean dependent records only after the table is present.
    if inspect(model.meta.engine).has_table(IATIFile.__tablename__):
        model.Session.query(IATIFile).delete(synchronize_session=False)
        model.Session.query(model.Resource).delete(synchronize_session=False)
        model.Session.commit()

    reset_db()
    migrate_db_for("iati_generator")
