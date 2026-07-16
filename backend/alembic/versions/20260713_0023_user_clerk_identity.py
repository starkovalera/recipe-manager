"""add Clerk identity and user lifecycle

Revision ID: 20260713_0023
Revises: 20260712_0022
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260713_0023"
down_revision: str | None = "20260712_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_status = sa.Enum("active", "deactivated", "deletion_pending", name="user_status")


def upgrade() -> None:
    user_status.create(op.get_bind(), checkfirst=True)
    op.add_column("users", sa.Column("clerk_user_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("status", user_status, server_default="active", nullable=False))
    op.add_column("users", sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.drop_column("users", "deletion_requested_at")
    op.drop_column("users", "status")
    op.drop_column("users", "clerk_user_id")
    user_status.drop(op.get_bind(), checkfirst=True)
