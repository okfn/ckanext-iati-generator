"""Remove IATIFile model.

Revision ID: 2c976b43b6d3
Revises: 1245d2d05f24
Create Date: 2026-02-16 10:54:29.611583

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '2c976b43b6d3'
down_revision = '1245d2d05f24'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('iati_files')


def downgrade():
    pass
