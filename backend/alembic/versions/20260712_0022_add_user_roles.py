"""add user roles

Revision ID: 20260712_0022
Revises: 20260712_0021
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260712_0022"
down_revision: str | None = "20260712_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_role_assignments",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.Enum("debug", "superadmin", name="user_role"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role"),
    )
    role_expression = "CAST(:role AS user_role)" if op.get_context().dialect.name == "postgresql" else ":role"
    seed_role = sa.text(f"INSERT INTO user_role_assignments (user_id, role) SELECT id, {role_expression} FROM users WHERE id = :user_id")
    for role in ("debug", "superadmin"):
        op.execute(seed_role.bindparams(user_id="local-user", role=role))


def downgrade() -> None:
    op.drop_table("user_role_assignments")
    if op.get_context().dialect.name == "postgresql":
        sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
