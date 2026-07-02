"""add background job metadata

Revision ID: 20260627_0004
Revises: 20260626_0003
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260627_0004"
down_revision = "20260626_0003"
branch_labels = None
depends_on = None


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.add_column("import_jobs", sa.Column("dedupe_key", sa.String(), nullable=True))
    op.execute("UPDATE import_jobs SET dedupe_key = client_import_id WHERE client_import_id IS NOT NULL")
    op.create_index("ix_import_jobs_owner_dedupe_key", "import_jobs", ["owner_id", "dedupe_key"], unique=True)

    if _is_postgresql():
        op.execute("ALTER TYPE importjobstatus RENAME TO importjobstatus_old")
        op.execute(
            "CREATE TYPE importjobstatus AS ENUM "
            "('QUEUED', 'RUNNING', 'SUCCEEDED', 'SUCCEEDED_WITH_FLAGS', 'FAILED', 'CANCELLED')"
        )
        op.execute(
            """
            ALTER TABLE import_jobs
            ALTER COLUMN status TYPE importjobstatus
            USING CASE status::text
              WHEN 'PENDING' THEN 'QUEUED'
              WHEN 'pending' THEN 'QUEUED'
              WHEN 'PROCESSING' THEN 'RUNNING'
              WHEN 'processing' THEN 'RUNNING'
              WHEN 'succeeded' THEN 'SUCCEEDED'
              WHEN 'failed' THEN 'FAILED'
              ELSE status::text
            END::importjobstatus
            """
        )
        op.execute("DROP TYPE importjobstatus_old")
    else:
        op.execute("UPDATE import_jobs SET status = 'QUEUED' WHERE status IN ('PENDING', 'pending')")
        op.execute("UPDATE import_jobs SET status = 'RUNNING' WHERE status IN ('PROCESSING', 'processing')")
        op.execute("UPDATE import_jobs SET status = 'SUCCEEDED' WHERE status = 'succeeded'")
        op.execute("UPDATE import_jobs SET status = 'FAILED' WHERE status = 'failed'")

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("entity_id", sa.String(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "job_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("import_job_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["import_job_id"], ["import_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("job_events")
    op.drop_table("notifications")
    op.drop_index("ix_import_jobs_owner_dedupe_key", table_name="import_jobs")
    op.drop_column("import_jobs", "dedupe_key")

    if _is_postgresql():
        op.execute("ALTER TYPE importjobstatus RENAME TO importjobstatus_new")
        op.execute("CREATE TYPE importjobstatus AS ENUM ('PENDING', 'PROCESSING', 'SUCCEEDED', 'FAILED')")
        op.execute(
            """
            ALTER TABLE import_jobs
            ALTER COLUMN status TYPE importjobstatus
            USING CASE status::text
              WHEN 'QUEUED' THEN 'PENDING'
              WHEN 'RUNNING' THEN 'PROCESSING'
              WHEN 'SUCCEEDED_WITH_FLAGS' THEN 'SUCCEEDED'
              ELSE status::text
            END::importjobstatus
            """
        )
        op.execute("DROP TYPE importjobstatus_new")
