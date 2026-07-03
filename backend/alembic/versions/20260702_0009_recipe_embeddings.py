"""add recipe embeddings

Revision ID: 20260702_0009
Revises: 20260629_0008
Create Date: 2026-07-02
"""

from alembic import op
import sqlalchemy as sa

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover - migration dependency is installed in normal runtime
    Vector = None


revision = "20260702_0009"
down_revision = "20260629_0008"
branch_labels = None
depends_on = None


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if _is_postgresql():
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        embedding_type = Vector(1536)
    else:
        embedding_type = sa.JSON()

    op.create_table(
        "recipe_embeddings",
        sa.Column("recipe_id", sa.String(), nullable=False),
        sa.Column("embedding", embedding_type, nullable=True),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("input_hash", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("recipe_id"),
    )


def downgrade() -> None:
    op.drop_table("recipe_embeddings")
