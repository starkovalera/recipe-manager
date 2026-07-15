"""add secondary resource failure import event

Revision ID: 20260711_0020
Revises: 20260710_0019
"""

import sqlalchemy as sa

from alembic import op

revision = "20260711_0020"
down_revision = "20260710_0019"
branch_labels = None
depends_on = None


OLD_IMPORT_EVENT_TYPE_ENUM = sa.Enum(
    "IMPORT_CREATED",
    "IMPORT_STARTED",
    "RAW_SOURCES_DOWNLOADED",
    "EXTRACTOR_REQUESTED",
    "EXTRACTOR_SUCCEEDED",
    "RECIPE_CREATED",
    "IMPORT_FAILED",
    name="importeventtype",
)

IMPORT_EVENT_TYPE_ENUM = sa.Enum(
    "IMPORT_CREATED",
    "IMPORT_STARTED",
    "RAW_SOURCES_DOWNLOADED",
    "IMPORT_SECONDARY_RESOURCE_UPLOAD_FAILED",
    "EXTRACTOR_REQUESTED",
    "EXTRACTOR_SUCCEEDED",
    "RECIPE_CREATED",
    "IMPORT_FAILED",
    name="importeventtype",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("ALTER TYPE importeventtype ADD VALUE IF NOT EXISTS 'IMPORT_SECONDARY_RESOURCE_UPLOAD_FAILED'")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.alter_column(
        "job_events",
        "event_type",
        existing_type=IMPORT_EVENT_TYPE_ENUM,
        type_=sa.String(),
        postgresql_using="event_type::text",
        existing_nullable=False,
    )
    op.execute("UPDATE job_events SET event_type = 'RAW_SOURCES_DOWNLOADED' WHERE event_type = 'IMPORT_SECONDARY_RESOURCE_UPLOAD_FAILED'")
    IMPORT_EVENT_TYPE_ENUM.drop(bind, checkfirst=True)
    OLD_IMPORT_EVENT_TYPE_ENUM.create(bind, checkfirst=True)
    op.alter_column(
        "job_events",
        "event_type",
        existing_type=sa.String(),
        type_=OLD_IMPORT_EVENT_TYPE_ENUM,
        postgresql_using="event_type::importeventtype",
        existing_nullable=False,
    )
