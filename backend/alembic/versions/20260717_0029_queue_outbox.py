"""add transactional queue outbox

Revision ID: 20260717_0029
Revises: 20260715_0028
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260717_0029"
down_revision: str | None = "20260715_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        postgresql.ENUM(
            "IMPORT_JOB",
            "RECIPE_EMBEDDING",
            "ACCOUNT_DELETION",
            name="queue_message_type",
        ).create(op.get_bind(), checkfirst=True)
        postgresql.ENUM(
            "PENDING",
            "PUBLISHED",
            name="queue_outbox_status",
        ).create(op.get_bind(), checkfirst=True)

    message_type = sa.Enum(
        "IMPORT_JOB",
        "RECIPE_EMBEDDING",
        "ACCOUNT_DELETION",
        name="queue_message_type",
    ).with_variant(
        postgresql.ENUM(
            "IMPORT_JOB",
            "RECIPE_EMBEDDING",
            "ACCOUNT_DELETION",
            name="queue_message_type",
            create_type=False,
        ),
        "postgresql",
    )
    outbox_status = sa.Enum(
        "PENDING",
        "PUBLISHED",
        name="queue_outbox_status",
    ).with_variant(
        postgresql.ENUM(
            "PENDING",
            "PUBLISHED",
            name="queue_outbox_status",
            create_type=False,
        ),
        "postgresql",
    )

    op.create_table(
        "queue_outbox_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("message_type", message_type, nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column(
            "status",
            outbox_status,
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_type", sa.String(length=255)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_queue_outbox_status_created_at",
        "queue_outbox_messages",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_queue_outbox_status_created_at",
        table_name="queue_outbox_messages",
    )
    op.drop_table("queue_outbox_messages")

    if op.get_context().dialect.name == "postgresql":
        postgresql.ENUM(
            "PENDING",
            "PUBLISHED",
            name="queue_outbox_status",
        ).drop(op.get_bind(), checkfirst=True)
        postgresql.ENUM(
            "IMPORT_JOB",
            "RECIPE_EMBEDDING",
            "ACCOUNT_DELETION",
            name="queue_message_type",
        ).drop(op.get_bind(), checkfirst=True)
