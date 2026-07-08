"""add import failed job error code

Revision ID: 20260708_0015
Revises: 20260707_0014
Create Date: 2026-07-08
"""

from alembic import op


revision = "20260708_0015"
down_revision = "20260707_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("ALTER TYPE importjoberrorcode ADD VALUE IF NOT EXISTS 'IMPORT_FAILED'")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # PostgreSQL cannot drop enum values directly. Keep the enum value in place
    # on downgrade; older code should not create new IMPORT_FAILED rows.
    op.execute("UPDATE import_jobs SET error_code = NULL WHERE error_code::text = 'IMPORT_FAILED'")
