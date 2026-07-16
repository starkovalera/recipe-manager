"""type import job event type

Revision ID: 20260707_0013
Revises: 20260705_0012
Create Date: 2026-07-07
"""

import sqlalchemy as sa

from alembic import op

revision = "20260707_0013"
down_revision = "20260705_0012"
branch_labels = None
depends_on = None


IMPORT_EVENT_TYPE_ENUM = sa.Enum(
    "IMPORT_CREATED",
    "IMPORT_STARTED",
    "RAW_SOURCES_DOWNLOADED",
    "EXTRACTOR_REQUESTED",
    "EXTRACTOR_SUCCEEDED",
    "RECIPE_CREATED",
    "IMPORT_FAILED",
    name="importeventtype",
)


OLD_TO_NEW_EVENT_TYPES = {
    "queued": "IMPORT_CREATED",
    "worker_started": "IMPORT_STARTED",
    "source_downloaded": "RAW_SOURCES_DOWNLOADED",
    "ai_called": "EXTRACTOR_REQUESTED",
    "ai_succeeded": "EXTRACTOR_SUCCEEDED",
    "recipe_created": "RECIPE_CREATED",
    "failed": "IMPORT_FAILED",
}


NEW_TO_OLD_EVENT_TYPES = {new: old for old, new in OLD_TO_NEW_EVENT_TYPES.items()}


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    IMPORT_EVENT_TYPE_ENUM.create(bind, checkfirst=True)
    for old_value, new_value in OLD_TO_NEW_EVENT_TYPES.items():
        op.execute(
            sa.text("UPDATE job_events SET event_type = :new_value WHERE event_type = :old_value").bindparams(
                old_value=old_value,
                new_value=new_value,
            )
        )
    op.alter_column(
        "job_events",
        "event_type",
        existing_type=sa.String(),
        type_=IMPORT_EVENT_TYPE_ENUM,
        postgresql_using="event_type::importeventtype",
        existing_nullable=False,
    )


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
    for new_value, old_value in NEW_TO_OLD_EVENT_TYPES.items():
        op.execute(
            sa.text("UPDATE job_events SET event_type = :old_value WHERE event_type = :new_value").bindparams(
                old_value=old_value,
                new_value=new_value,
            )
        )
    IMPORT_EVENT_TYPE_ENUM.drop(bind, checkfirst=True)
