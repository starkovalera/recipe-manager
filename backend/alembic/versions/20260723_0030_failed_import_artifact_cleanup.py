"""add failed import artifact cleanup state

Revision ID: 20260723_0030
Revises: 20260717_0029
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260723_0030"
down_revision: str | None = "20260717_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_IMPORT_JOB_STATUS = sa.Enum(
    "QUEUED",
    "RUNNING",
    "SUCCEEDED",
    "SUCCEEDED_WITH_FLAGS",
    "FAILED",
    "CANCELLED",
    name="importjobstatus",
)

IMPORT_JOB_STATUS = sa.Enum(
    "QUEUED",
    "RUNNING",
    "SUCCEEDED",
    "SUCCEEDED_WITH_FLAGS",
    "FAILED",
    "FAILED_ARTIFACTS_REMOVED",
    "CANCELLED",
    name="importjobstatus",
)

OLD_IMPORT_EVENT_TYPE = sa.Enum(
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

IMPORT_EVENT_TYPE = sa.Enum(
    "IMPORT_CREATED",
    "IMPORT_STARTED",
    "RAW_SOURCES_DOWNLOADED",
    "IMPORT_SECONDARY_RESOURCE_UPLOAD_FAILED",
    "EXTRACTOR_REQUESTED",
    "EXTRACTOR_SUCCEEDED",
    "RECIPE_CREATED",
    "IMPORT_FAILED",
    "IMPORT_ARTIFACTS_REMOVED",
    name="importeventtype",
)


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    op.execute("ALTER TYPE importjobstatus ADD VALUE IF NOT EXISTS 'FAILED_ARTIFACTS_REMOVED'")
    op.execute("ALTER TYPE importeventtype ADD VALUE IF NOT EXISTS 'IMPORT_ARTIFACTS_REMOVED'")


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    bind = op.get_bind()
    op.alter_column(
        "import_jobs",
        "status",
        existing_type=IMPORT_JOB_STATUS,
        type_=sa.String(),
        postgresql_using="status::text",
        existing_nullable=False,
    )
    op.execute("UPDATE import_jobs SET status = 'FAILED' WHERE status = 'FAILED_ARTIFACTS_REMOVED'")
    IMPORT_JOB_STATUS.drop(bind, checkfirst=True)
    OLD_IMPORT_JOB_STATUS.create(bind, checkfirst=True)
    op.alter_column(
        "import_jobs",
        "status",
        existing_type=sa.String(),
        type_=OLD_IMPORT_JOB_STATUS,
        postgresql_using="status::importjobstatus",
        existing_nullable=False,
    )

    op.alter_column(
        "job_events",
        "event_type",
        existing_type=IMPORT_EVENT_TYPE,
        type_=sa.String(),
        postgresql_using="event_type::text",
        existing_nullable=False,
    )
    op.execute("UPDATE job_events SET event_type = 'IMPORT_FAILED' WHERE event_type = 'IMPORT_ARTIFACTS_REMOVED'")
    IMPORT_EVENT_TYPE.drop(bind, checkfirst=True)
    OLD_IMPORT_EVENT_TYPE.create(bind, checkfirst=True)
    op.alter_column(
        "job_events",
        "event_type",
        existing_type=sa.String(),
        type_=OLD_IMPORT_EVENT_TYPE,
        postgresql_using="event_type::importeventtype",
        existing_nullable=False,
    )
