"""type notification type and entity type

Revision ID: 20260707_0014
Revises: 20260707_0013
Create Date: 2026-07-07
"""

import sqlalchemy as sa

from alembic import op

revision = "20260707_0014"
down_revision = "20260707_0013"
branch_labels = None
depends_on = None


NOTIFICATION_TYPE_ENUM = sa.Enum(
    "IMPORT_STARTED",
    "IMPORT_FAILED",
    "IMPORT_SUCCEEDED",
    "IMPORT_SUCCEEDED_WITH_FLAGS",
    name="notificationtype",
)

NOTIFICATION_ENTITY_TYPE_ENUM = sa.Enum(
    "RECIPE",
    "IMPORT_JOB",
    name="notificationentitytype",
)


OLD_TO_NEW_NOTIFICATION_TYPES = {
    "import_started": "IMPORT_STARTED",
    "import_failed": "IMPORT_FAILED",
    "import_succeeded": "IMPORT_SUCCEEDED",
    "import_succeeded_with_flags": "IMPORT_SUCCEEDED_WITH_FLAGS",
}

OLD_TO_NEW_ENTITY_TYPES = {
    "recipe": "RECIPE",
    "import_job": "IMPORT_JOB",
}


NEW_TO_OLD_NOTIFICATION_TYPES = {new: old for old, new in OLD_TO_NEW_NOTIFICATION_TYPES.items()}
NEW_TO_OLD_ENTITY_TYPES = {new: old for old, new in OLD_TO_NEW_ENTITY_TYPES.items()}


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    NOTIFICATION_TYPE_ENUM.create(bind, checkfirst=True)
    NOTIFICATION_ENTITY_TYPE_ENUM.create(bind, checkfirst=True)
    for old_value, new_value in OLD_TO_NEW_NOTIFICATION_TYPES.items():
        op.execute(
            sa.text("UPDATE notifications SET type = :new_value WHERE type = :old_value").bindparams(
                old_value=old_value,
                new_value=new_value,
            )
        )
    for old_value, new_value in OLD_TO_NEW_ENTITY_TYPES.items():
        op.execute(
            sa.text("UPDATE notifications SET entity_type = :new_value WHERE entity_type = :old_value").bindparams(
                old_value=old_value,
                new_value=new_value,
            )
        )
    op.alter_column(
        "notifications",
        "type",
        existing_type=sa.String(),
        type_=NOTIFICATION_TYPE_ENUM,
        postgresql_using="type::notificationtype",
        existing_nullable=False,
    )
    op.alter_column(
        "notifications",
        "entity_type",
        existing_type=sa.String(),
        type_=NOTIFICATION_ENTITY_TYPE_ENUM,
        postgresql_using="entity_type::notificationentitytype",
        existing_nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.alter_column(
        "notifications",
        "entity_type",
        existing_type=NOTIFICATION_ENTITY_TYPE_ENUM,
        type_=sa.String(),
        postgresql_using="entity_type::text",
        existing_nullable=True,
    )
    op.alter_column(
        "notifications",
        "type",
        existing_type=NOTIFICATION_TYPE_ENUM,
        type_=sa.String(),
        postgresql_using="type::text",
        existing_nullable=False,
    )
    for new_value, old_value in NEW_TO_OLD_NOTIFICATION_TYPES.items():
        op.execute(
            sa.text("UPDATE notifications SET type = :old_value WHERE type = :new_value").bindparams(
                old_value=old_value,
                new_value=new_value,
            )
        )
    for new_value, old_value in NEW_TO_OLD_ENTITY_TYPES.items():
        op.execute(
            sa.text("UPDATE notifications SET entity_type = :old_value WHERE entity_type = :new_value").bindparams(
                old_value=old_value,
                new_value=new_value,
            )
        )
    NOTIFICATION_ENTITY_TYPE_ENUM.drop(bind, checkfirst=True)
    NOTIFICATION_TYPE_ENUM.drop(bind, checkfirst=True)
