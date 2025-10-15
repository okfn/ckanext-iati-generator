"""Add ON DELETE CASCADE to iati_files.resource_id FK

Revision ID: c1b2c1a3d93d
Revises: 1245d2d05f24
Create Date: 2025-10-15 14:39:50.769792

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1b2c1a3d93d'
down_revision = '1245d2d05f24'
branch_labels = None
depends_on = None


def upgrade():

    op.alter_column(
        "iati_files",
        "namespace",
        existing_type=sa.Text(),
        type_=sa.String(length=90),
        existing_nullable=False,
        nullable=True,
        postgresql_using="left(namespace, 90)",
    )


def downgrade():
    op.alter_column(
        "iati_files",
        "namespace",
        existing_type=sa.String(length=90),
        type_=sa.Text(),
        existing_nullable=True,
        nullable=False,
    )
