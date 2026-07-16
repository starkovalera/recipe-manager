"""add import attempt count

Revision ID: 20260710_0019
Revises: 20260710_0018
"""

import sqlalchemy as sa

from alembic import op

revision = "20260710_0019"
down_revision = "20260710_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "import_jobs",
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("import_jobs", "attempt_count")
