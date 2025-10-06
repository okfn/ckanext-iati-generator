"""IATI files model

Revision ID: 1245d2d05f24
Revises:
Create Date: 2025-10-02 16:11:18.057546

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1245d2d05f24'
down_revision = '1245d2d05f23'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('iati_files', sa.Column('is_valid', sa.Boolean, nullable=False, default=False))
    op.add_column('iati_files', sa.Column('last_processed', sa.DateTime, nullable=True))
    op.add_column('iati_files', sa.Column('last_processed_success', sa.DateTime, nullable=True))
    op.add_column('iati_files', sa.Column('last_error', sa.UnicodeText, nullable=True))


def downgrade():
    op.drop_column('iati_files', 'is_valid')
    op.drop_column('iati_files', 'last_processed')
    op.drop_column('iati_files', 'last_processed_success')
    op.drop_column('iati_files', 'last_error')
