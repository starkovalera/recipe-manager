"""add recipe source tree

Revision ID: 20260626_0002
Revises: 20260625_0001
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa

revision = "20260626_0002"
down_revision = "20260625_0001"
branch_labels = None
depends_on = None


source_origin = sa.Enum("MANUAL", "URL", "URL_VIDEO", name="recipesourceorigin")


def upgrade() -> None:
    with op.batch_alter_table("recipe_sources") as batch_op:
        batch_op.add_column(sa.Column("parent_source_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("source", source_origin, nullable=True))
    op.execute("UPDATE recipe_sources SET source = 'MANUAL' WHERE source IS NULL")
    with op.batch_alter_table("recipe_sources") as batch_op:
        batch_op.alter_column("source", existing_type=source_origin, nullable=False)
        batch_op.create_foreign_key(
            "fk_recipe_sources_parent_source_id",
            "recipe_sources",
            ["parent_source_id"],
            ["id"],
            ondelete="NO ACTION",
        )


def downgrade() -> None:
    with op.batch_alter_table("recipe_sources") as batch_op:
        batch_op.drop_constraint("fk_recipe_sources_parent_source_id", type_="foreignkey")
        batch_op.drop_column("source")
        batch_op.drop_column("parent_source_id")
