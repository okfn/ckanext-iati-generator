"""IATI files model

Revision ID: 1245d2d05f23
Revises: 
Create Date: 2025-10-02 16:11:18.057546

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1245d2d05f23'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'iati_files',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('file_type', sa.Integer, nullable=False),
        sa.Column(
            'resource_id',
            sa.UnicodeText,
            sa.ForeignKey('resource.id', ondelete='CASCADE'),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column('metadata_created', sa.DateTime, server_default=sa.func.now()),
        sa.Column('metadata_updated', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade():
    op.drop_table('iati_files')
