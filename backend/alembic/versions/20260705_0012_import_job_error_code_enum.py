"""type import job error code

Revision ID: 20260705_0012
Revises: 20260705_0011
Create Date: 2026-07-05
"""

import sqlalchemy as sa
from alembic import op


revision = "20260705_0012"
down_revision = "20260705_0011"
branch_labels = None
depends_on = None


ERROR_CODE_ENUM = sa.Enum(
    "IMPORT_CREATION_FAILED",
    "IMPORT_PROCESSING_FAILED",
    "IMPORT_EXTRACTION_FAILED",
    name="importjoberrorcode",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        ERROR_CODE_ENUM.create(bind, checkfirst=True)
        op.execute(
            "UPDATE import_jobs SET error_code = 'IMPORT_EXTRACTION_FAILED' "
            "WHERE error_code IN ('AI_UNAVAILABLE', 'NOT_A_RECIPE', 'RECIPE_TOO_LONG', 'INVALID_EXTRACTION_RESULT')"
        )
        op.alter_column(
            "import_jobs",
            "error_code",
            existing_type=sa.String(),
            type_=ERROR_CODE_ENUM,
            postgresql_using="error_code::importjoberrorcode",
            existing_nullable=True,
        )
    else:
        return


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "import_jobs",
            "error_code",
            existing_type=ERROR_CODE_ENUM,
            type_=sa.String(),
            postgresql_using="error_code::text",
            existing_nullable=True,
        )
        ERROR_CODE_ENUM.drop(bind, checkfirst=True)
    else:
        return
