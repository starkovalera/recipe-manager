"""replace provider-specific user identity with generic auth identity

Revision ID: 20260714_0024
Revises: 20260713_0023
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260714_0024"
down_revision: str | None = "20260713_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

auth_provider = sa.Enum("CLERK", name="auth_provider")


def upgrade() -> None:
    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.alter_column("users", "clerk_user_id", new_column_name="auth_user_id")
    auth_provider.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column("auth_provider", auth_provider, server_default="CLERK", nullable=False),
    )
    op.create_index(
        "ix_users_auth_identity",
        "users",
        ["auth_provider", "auth_user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_users_auth_identity", table_name="users")
    op.drop_column("users", "auth_provider")
    op.alter_column("users", "auth_user_id", new_column_name="clerk_user_id")
    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"], unique=True)
    auth_provider.drop(op.get_bind(), checkfirst=True)
