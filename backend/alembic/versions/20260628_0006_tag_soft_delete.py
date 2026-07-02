"""add tag soft delete fields

Revision ID: 20260628_0006
Revises: 20260628_0005
Create Date: 2026-06-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260628_0006"
down_revision = "20260628_0005"
branch_labels = None
depends_on = None


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.add_column("tags", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("tags", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    if _is_postgresql():
        op.drop_constraint("tags_owner_id_name_key", "tags", type_="unique")
        op.execute(
            """
            CREATE UNIQUE INDEX ix_tags_owner_lower_name_active_unique
            ON tags (owner_id, lower(name))
            WHERE deleted_at IS NULL
            """
        )


def downgrade() -> None:
    if _is_postgresql():
        op.drop_index("ix_tags_owner_lower_name_active_unique", table_name="tags")
        op.create_unique_constraint("tags_owner_id_name_key", "tags", ["owner_id", "name"])
    op.drop_column("tags", "deleted_at")
    op.drop_column("tags", "description")
