"""add recipe cover image foreign key

Revision ID: 20260710_0016
Revises: 20260708_0015
Create Date: 2026-07-10
"""

from alembic import op

revision = "20260710_0016"
down_revision = "20260708_0015"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "fk_recipes_cover_image_id_recipe_images"


def upgrade() -> None:
    op.execute(
        """
        UPDATE recipes
        SET cover_image_id = NULL
        WHERE cover_image_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM recipe_images
              WHERE recipe_images.id = recipes.cover_image_id
          )
        """
    )
    with op.batch_alter_table("recipes") as batch_op:
        batch_op.create_foreign_key(
            CONSTRAINT_NAME,
            "recipe_images",
            ["cover_image_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("recipes") as batch_op:
        batch_op.drop_constraint(CONSTRAINT_NAME, type_="foreignkey")
