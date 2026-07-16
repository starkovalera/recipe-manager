"""set deleted import recipe reference to null

Revision ID: 20260712_0021
Revises: 20260711_0020
"""

from alembic import op

revision = "20260712_0021"
down_revision = "20260711_0020"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "fk_import_jobs_created_recipe_id_recipes"
SQLITE_NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("import_jobs_created_recipe_id_fkey", "import_jobs", type_="foreignkey")
        op.create_foreign_key(
            CONSTRAINT_NAME,
            "import_jobs",
            "recipes",
            ["created_recipe_id"],
            ["id"],
            ondelete="SET NULL",
        )
        return

    with op.batch_alter_table("import_jobs", naming_convention=SQLITE_NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint(CONSTRAINT_NAME, type_="foreignkey")
        batch_op.create_foreign_key(
            CONSTRAINT_NAME,
            "recipes",
            ["created_recipe_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint(CONSTRAINT_NAME, "import_jobs", type_="foreignkey")
        op.create_foreign_key(
            "import_jobs_created_recipe_id_fkey",
            "import_jobs",
            "recipes",
            ["created_recipe_id"],
            ["id"],
            ondelete="NO ACTION",
        )
        return

    with op.batch_alter_table("import_jobs", naming_convention=SQLITE_NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint(CONSTRAINT_NAME, type_="foreignkey")
        batch_op.create_foreign_key(
            CONSTRAINT_NAME,
            "recipes",
            ["created_recipe_id"],
            ["id"],
            ondelete="NO ACTION",
        )
