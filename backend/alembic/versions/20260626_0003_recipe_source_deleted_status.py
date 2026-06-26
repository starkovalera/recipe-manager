"""add deleted recipe source status

Revision ID: 20260626_0003
Revises: 20260626_0002
Create Date: 2026-06-26
"""

revision = "20260626_0003"
down_revision = "20260626_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite stores SQLAlchemy Enum values as strings here, so no table rewrite
    # is required to allow the new DELETED value.
    pass


def downgrade() -> None:
    pass
