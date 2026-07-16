"""add embedding events

Revision ID: 20260703_0010
Revises: 20260702_0009
Create Date: 2026-07-03
"""

import sqlalchemy as sa

from alembic import op

revision = "20260703_0010"
down_revision = "20260702_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "embedding_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("recipe_id", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("status_after", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipe_embeddings.recipe_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_embedding_events_recipe_created_at", "embedding_events", ["recipe_id", "created_at"])
    op.create_index("ix_embedding_events_owner_created_at", "embedding_events", ["owner_id", "created_at"])
    op.create_index("ix_embedding_events_type_created_at", "embedding_events", ["event_type", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_embedding_events_type_created_at", table_name="embedding_events")
    op.drop_index("ix_embedding_events_owner_created_at", table_name="embedding_events")
    op.drop_index("ix_embedding_events_recipe_created_at", table_name="embedding_events")
    op.drop_table("embedding_events")
