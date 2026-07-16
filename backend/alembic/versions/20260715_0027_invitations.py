"""add invitations

Revision ID: 20260715_0027
Revises: 20260714_0026
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260715_0027"
down_revision: str | None = "20260714_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    auth_provider = sa.Enum("CLERK", name="auth_provider").with_variant(
        postgresql.ENUM("CLERK", name="auth_provider", create_type=False),
        "postgresql",
    )
    op.create_table(
        "invitations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("auth_provider", auth_provider, nullable=False),
        sa.Column("auth_invitation_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "ACCEPTED", "REVOKED", "EXPIRED", name="invitation_status"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invitations_auth_identity", "invitations", ["auth_provider", "auth_invitation_id"], unique=True)
    op.create_index("ix_invitations_email", "invitations", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_invitations_email", table_name="invitations")
    op.drop_index("ix_invitations_auth_identity", table_name="invitations")
    op.drop_table("invitations")
