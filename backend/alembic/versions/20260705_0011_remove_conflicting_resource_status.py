"""remove conflicting recipe resource status

Revision ID: 20260705_0011
Revises: 20260703_0010
Create Date: 2026-07-05
"""

from alembic import op

revision = "20260705_0011"
down_revision = "20260703_0010"
branch_labels = None
depends_on = None


OLD_ENUM = "reciperesourcestatus"
NEW_ENUM = "reciperesourcestatus_new"
OLD_VALUES = ("USED", "IGNORED", "CONFLICTING", "UNKNOWN", "DELETED")
NEW_VALUES = ("USED", "IGNORED", "UNKNOWN", "DELETED")


def _replace_postgres_enum(values: tuple[str, ...]) -> None:
    op.execute("UPDATE recipe_resources SET status = 'UNKNOWN' WHERE status::text = 'CONFLICTING'")
    op.execute(f"ALTER TYPE {OLD_ENUM} RENAME TO {OLD_ENUM}_old")
    op.execute(f"CREATE TYPE {NEW_ENUM} AS ENUM ({', '.join(repr(value) for value in values)})")
    op.execute(f"ALTER TABLE recipe_resources ALTER COLUMN status TYPE {NEW_ENUM} USING status::text::{NEW_ENUM}")
    op.execute(f"DROP TYPE {OLD_ENUM}_old")
    op.execute(f"ALTER TYPE {NEW_ENUM} RENAME TO {OLD_ENUM}")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    _replace_postgres_enum(NEW_VALUES)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    _replace_postgres_enum(OLD_VALUES)
