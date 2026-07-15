"""add recipe deletion status

Revision ID: 20260715_0028
Revises: 20260715_0027
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260715_0028"
down_revision: str | None = "20260715_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        postgresql.ENUM("ACTIVE", "DELETION_PENDING", name="recipe_status").create(op.get_bind(), checkfirst=True)
    recipe_status = sa.Enum("ACTIVE", "DELETION_PENDING", name="recipe_status").with_variant(
        postgresql.ENUM("ACTIVE", "DELETION_PENDING", name="recipe_status", create_type=False),
        "postgresql",
    )
    op.add_column(
        "recipes",
        sa.Column("status", recipe_status, server_default="ACTIVE", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("recipes", "status")
    if op.get_context().dialect.name == "postgresql":
        postgresql.ENUM("ACTIVE", "DELETION_PENDING", name="recipe_status").drop(op.get_bind(), checkfirst=True)
