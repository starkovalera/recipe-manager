"""add ingredient search name

Revision ID: 20260629_0007
Revises: 20260628_0006
Create Date: 2026-06-29
"""

import sqlalchemy as sa

from alembic import op

revision = "20260629_0007"
down_revision = "20260628_0006"
branch_labels = None
depends_on = None


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.add_column("ingredients", sa.Column("search_name", sa.String(), nullable=True))
    if _is_postgresql():
        op.execute("UPDATE ingredients SET search_name = lower(trim(regexp_replace(name, '\\s+', ' ', 'g')))")
    else:
        op.execute("UPDATE ingredients SET search_name = lower(trim(name))")
    with op.batch_alter_table("ingredients") as batch_op:
        batch_op.alter_column("search_name", existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("ingredients") as batch_op:
        batch_op.drop_column("search_name")
