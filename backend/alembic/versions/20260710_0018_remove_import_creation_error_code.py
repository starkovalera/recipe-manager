"""remove import creation job error code

Revision ID: 20260710_0018
Revises: 20260710_0017
Create Date: 2026-07-10
"""

from alembic import op

revision = "20260710_0018"
down_revision = "20260710_0017"
branch_labels = None
depends_on = None


ENUM_NAME = "importjoberrorcode"
TEMP_ENUM_NAME = "importjoberrorcode_new"
OLD_VALUES = (
    "IMPORT_CREATION_FAILED",
    "IMPORT_PROCESSING_FAILED",
    "IMPORT_EXTRACTION_FAILED",
    "IMPORT_FAILED",
)
NEW_VALUES = (
    "IMPORT_PROCESSING_FAILED",
    "IMPORT_EXTRACTION_FAILED",
    "IMPORT_FAILED",
)


def _replace_postgres_enum(values: tuple[str, ...], value_mapping: dict[str, str] | None = None) -> None:
    value_expression = "error_code::text"
    if value_mapping:
        cases = " ".join(f"WHEN {old_value!r} THEN {new_value!r}" for old_value, new_value in value_mapping.items())
        value_expression = f"CASE error_code::text {cases} ELSE error_code::text END"

    op.execute(f"ALTER TYPE {ENUM_NAME} RENAME TO {ENUM_NAME}_old")
    op.execute(f"CREATE TYPE {TEMP_ENUM_NAME} AS ENUM ({', '.join(repr(value) for value in values)})")
    op.execute(
        f"ALTER TABLE import_jobs ALTER COLUMN error_code TYPE {TEMP_ENUM_NAME} "
        f"USING ({value_expression})::{TEMP_ENUM_NAME}"
    )
    op.execute(f"DROP TYPE {ENUM_NAME}_old")
    op.execute(f"ALTER TYPE {TEMP_ENUM_NAME} RENAME TO {ENUM_NAME}")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _replace_postgres_enum(
            NEW_VALUES,
            value_mapping={"IMPORT_CREATION_FAILED": "IMPORT_FAILED"},
        )
        return

    op.execute(
        "UPDATE import_jobs SET error_code = 'IMPORT_FAILED' "
        "WHERE error_code = 'IMPORT_CREATION_FAILED'"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        # Restoring the enum member cannot reconstruct the previous per-row classification.
        _replace_postgres_enum(OLD_VALUES)
