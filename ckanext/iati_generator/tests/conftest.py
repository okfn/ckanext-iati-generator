import pytest
from ckan import model

from ckanext.iati_generator.models.iati_files import IATIFile


@pytest.fixture
def clean_db(reset_db, migrate_db_for):
    """Clean and initialize the database."""
    model.Session.rollback()
    model.Session.query(IATIFile).delete(synchronize_session=False)
    model.Session.query(model.Resource).delete(synchronize_session=False)
    model.Session.commit()
    reset_db()
    migrate_db_for("iati_generator")
