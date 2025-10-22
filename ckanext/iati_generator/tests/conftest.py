import pytest


@pytest.fixture
def clean_db(reset_db, migrate_db_for, with_plugins):
    """Clean and initialize the database."""
    reset_db()
    migrate_db_for("iati_generator")
