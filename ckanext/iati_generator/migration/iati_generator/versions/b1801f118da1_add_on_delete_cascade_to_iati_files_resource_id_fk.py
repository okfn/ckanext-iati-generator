"""Add ON DELETE CASCADE to iati_files.resource_id foreign key

This migration updates the foreign key constraint on the `iati_files.resource_id`
column so that when a related resource is deleted, its corresponding
IATIFile entry is automatically removed.

Revision ID: b1801f118da1
Revises: 1245d2d05f24
Create Date: 2025-10-16 13:43:39.036446

"""
from alembic import op
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'b1801f118da1'
down_revision = '1245d2d05f24'
branch_labels = None
depends_on = None


def _find_fk_name(inspector: Inspector, table: str, local_cols: list, referred_table: str):
    for fk in inspector.get_foreign_keys(table):
        if fk.get("referred_table") == referred_table and fk.get("constrained_columns") == local_cols:
            return fk.get("name")
    return None


def upgrade():
    bind = op.get_bind()
    insp = Inspector.from_engine(bind)

    fk_name = _find_fk_name(insp, "iati_files", ["resource_id"], "resource")
    if fk_name:
        op.drop_constraint(fk_name, "iati_files", type_="foreignkey")

    op.create_foreign_key(
        "iati_files_resource_id_fkey",
        "iati_files",
        "resource",
        ["resource_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    bind = op.get_bind()
    insp = Inspector.from_engine(bind)
    try:
        op.drop_constraint("iati_files_resource_id_fkey", "iati_files", type_="foreignkey")
    except Exception:
        fk_name = _find_fk_name(insp, "iati_files", ["resource_id"], "resource")
        if fk_name:
            op.drop_constraint(fk_name, "iati_files", type_="foreignkey")

    op.create_foreign_key(
        "iati_files_resource_id_fkey",
        "iati_files",
        "resource",
        ["resource_id"],
        ["id"],
        ondelete=None,
    )
