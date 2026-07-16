"""type embedding lifecycle fields

Revision ID: 20260710_0017
Revises: 20260710_0016
Create Date: 2026-07-10
"""

import sqlalchemy as sa

from alembic import op

revision = "20260710_0017"
down_revision = "20260710_0016"
branch_labels = None
depends_on = None


RECIPE_EMBEDDING_STATUS_ENUM = sa.Enum(
    "STALE",
    "RUNNING",
    "READY",
    "FAILED",
    "SKIPPED_DUE_TO_FLAGS",
    name="recipe_embedding_status",
)

RECIPE_EMBEDDING_EVENT_TYPE_ENUM = sa.Enum(
    "SCHEDULED",
    "ENQUEUED",
    "STARTED",
    "SKIPPED_DUE_TO_FLAGS",
    "ALREADY_READY",
    "PROVIDER_SUCCEEDED",
    "SAVED",
    "STALE_REQUEUED",
    "FAILED",
    "RETRY_REQUESTED",
    name="recipe_embedding_event_type",
)

OLD_TO_NEW_STATUSES = {
    "stale": "STALE",
    "running": "RUNNING",
    "ready": "READY",
    "failed": "FAILED",
    "skipped_due_to_flags": "SKIPPED_DUE_TO_FLAGS",
}

OLD_TO_NEW_EVENT_TYPES = {
    "scheduled": "SCHEDULED",
    "enqueued": "ENQUEUED",
    "started": "STARTED",
    "skipped_due_to_flags": "SKIPPED_DUE_TO_FLAGS",
    "already_ready": "ALREADY_READY",
    "provider_succeeded": "PROVIDER_SUCCEEDED",
    "saved": "SAVED",
    "stale_requeued": "STALE_REQUEUED",
    "failed": "FAILED",
    "retry_requested": "RETRY_REQUESTED",
}

NEW_TO_OLD_STATUSES = {new: old for old, new in OLD_TO_NEW_STATUSES.items()}
NEW_TO_OLD_EVENT_TYPES = {new: old for old, new in OLD_TO_NEW_EVENT_TYPES.items()}


def _replace_values(table: str, column: str, mapping: dict[str, str]) -> None:
    for old_value, new_value in mapping.items():
        op.execute(
            sa.text(f"UPDATE {table} SET {column} = :new_value WHERE {column} = :old_value").bindparams(
                old_value=old_value,
                new_value=new_value,
            )
        )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        RECIPE_EMBEDDING_STATUS_ENUM.create(bind, checkfirst=True)
        RECIPE_EMBEDDING_EVENT_TYPE_ENUM.create(bind, checkfirst=True)

    _replace_values("recipe_embeddings", "status", OLD_TO_NEW_STATUSES)
    _replace_values("embedding_events", "status_after", OLD_TO_NEW_STATUSES)
    _replace_values("embedding_events", "event_type", OLD_TO_NEW_EVENT_TYPES)

    if bind.dialect.name != "postgresql":
        return

    op.alter_column(
        "recipe_embeddings",
        "status",
        existing_type=sa.String(),
        type_=RECIPE_EMBEDDING_STATUS_ENUM,
        postgresql_using="status::recipe_embedding_status",
        existing_nullable=False,
    )
    op.alter_column(
        "embedding_events",
        "event_type",
        existing_type=sa.String(),
        type_=RECIPE_EMBEDDING_EVENT_TYPE_ENUM,
        postgresql_using="event_type::recipe_embedding_event_type",
        existing_nullable=False,
    )
    op.alter_column(
        "embedding_events",
        "status_after",
        existing_type=sa.String(),
        type_=RECIPE_EMBEDDING_STATUS_ENUM,
        postgresql_using="status_after::recipe_embedding_status",
        existing_nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "embedding_events",
            "status_after",
            existing_type=RECIPE_EMBEDDING_STATUS_ENUM,
            type_=sa.String(),
            postgresql_using="status_after::text",
            existing_nullable=True,
        )
        op.alter_column(
            "embedding_events",
            "event_type",
            existing_type=RECIPE_EMBEDDING_EVENT_TYPE_ENUM,
            type_=sa.String(),
            postgresql_using="event_type::text",
            existing_nullable=False,
        )
        op.alter_column(
            "recipe_embeddings",
            "status",
            existing_type=RECIPE_EMBEDDING_STATUS_ENUM,
            type_=sa.String(),
            postgresql_using="status::text",
            existing_nullable=False,
        )

    _replace_values("recipe_embeddings", "status", NEW_TO_OLD_STATUSES)
    _replace_values("embedding_events", "status_after", NEW_TO_OLD_STATUSES)
    _replace_values("embedding_events", "event_type", NEW_TO_OLD_EVENT_TYPES)

    if bind.dialect.name == "postgresql":
        RECIPE_EMBEDDING_EVENT_TYPE_ENUM.drop(bind, checkfirst=True)
        RECIPE_EMBEDDING_STATUS_ENUM.drop(bind, checkfirst=True)
