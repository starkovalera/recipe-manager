"""normalize user enum values to uppercase

Revision ID: 20260714_0025
Revises: 20260714_0024
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260714_0025"
down_revision: str | None = "20260714_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        op.execute("ALTER TYPE user_role RENAME VALUE 'debug' TO 'DEBUG'")
        op.execute("ALTER TYPE user_role RENAME VALUE 'superadmin' TO 'SUPERADMIN'")
        op.execute("ALTER TYPE user_status RENAME VALUE 'active' TO 'ACTIVE'")
        op.execute("ALTER TYPE user_status RENAME VALUE 'deactivated' TO 'DEACTIVATED'")
        op.execute("ALTER TYPE user_status RENAME VALUE 'deletion_pending' TO 'DELETION_PENDING'")
        op.alter_column("users", "status", server_default=sa.text("'ACTIVE'::user_status"))
        return

    op.execute("UPDATE user_role_assignments SET role = UPPER(role)")
    op.execute("UPDATE users SET status = UPPER(status)")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=16),
            server_default="ACTIVE",
            existing_nullable=False,
        )


def downgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        op.execute("ALTER TYPE user_role RENAME VALUE 'DEBUG' TO 'debug'")
        op.execute("ALTER TYPE user_role RENAME VALUE 'SUPERADMIN' TO 'superadmin'")
        op.execute("ALTER TYPE user_status RENAME VALUE 'ACTIVE' TO 'active'")
        op.execute("ALTER TYPE user_status RENAME VALUE 'DEACTIVATED' TO 'deactivated'")
        op.execute("ALTER TYPE user_status RENAME VALUE 'DELETION_PENDING' TO 'deletion_pending'")
        op.alter_column("users", "status", server_default=sa.text("'active'::user_status"))
        return

    op.execute("UPDATE user_role_assignments SET role = LOWER(role)")
    op.execute("UPDATE users SET status = LOWER(status)")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=16),
            server_default="active",
            existing_nullable=False,
        )
