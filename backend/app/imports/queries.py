from datetime import datetime

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import ImportJob, ImportJobSource, ImportJobStatus, QueueOutboxMessage
from app.queueing.constants import QueueMessageType, QueueOutboxStatus


def list_internal_import_jobs(session: Session, *, owner_id: str | None = None) -> list[ImportJob]:
    statement = (
        select(ImportJob).options(selectinload(ImportJob.sources), selectinload(ImportJob.events)).order_by(ImportJob.created_at.desc())
    )
    if owner_id is not None:
        statement = statement.where(ImportJob.owner_id == owner_id)
    return list(session.scalars(statement))


def get_import_job_unscoped(session: Session, job_id: str) -> ImportJob | None:
    return session.get(ImportJob, job_id)


def get_import_job_unscoped_for_update(session: Session, job_id: str) -> ImportJob | None:
    return session.scalar(select(ImportJob).where(ImportJob.id == job_id).with_for_update())


def list_stale_import_job_ids(
    session: Session,
    *,
    cutoff: datetime,
    limit: int,
) -> list[str]:
    statement = (
        select(ImportJob.id)
        .where(
            or_(
                and_(ImportJob.status == ImportJobStatus.QUEUED, ImportJob.updated_at <= cutoff),
                and_(
                    ImportJob.status == ImportJobStatus.RUNNING,
                    ImportJob.started_at.is_not(None),
                    ImportJob.started_at <= cutoff,
                ),
            )
        )
        .order_by(ImportJob.updated_at, ImportJob.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return list(session.scalars(statement))


def list_failed_import_artifact_cleanup_candidate_ids(
    session: Session,
    *,
    cutoff: datetime,
    limit: int,
) -> list[str]:
    pending_import_message = exists().where(
        QueueOutboxMessage.status == QueueOutboxStatus.PENDING,
        QueueOutboxMessage.message_type == QueueMessageType.IMPORT_JOB,
        QueueOutboxMessage.entity_id == ImportJob.id,
    )
    statement = (
        select(ImportJob.id)
        .where(
            ImportJob.status == ImportJobStatus.FAILED,
            ImportJob.finished_at.is_not(None),
            ImportJob.finished_at <= cutoff,
            ImportJob.created_recipe_id.is_(None),
            ~pending_import_message,
        )
        .order_by(ImportJob.finished_at, ImportJob.id)
        .limit(limit)
    )
    return list(session.scalars(statement))


def list_import_job_sources(session: Session, import_job_id: str) -> list[ImportJobSource]:
    return list(
        session.scalars(select(ImportJobSource).where(ImportJobSource.import_job_id == import_job_id).order_by(ImportJobSource.position))
    )


def get_import_job(session: Session, job_id: str, owner_id: str) -> ImportJob | None:
    return session.scalar(select(ImportJob).where(ImportJob.id == job_id, ImportJob.owner_id == owner_id))


def get_import_job_for_update(session: Session, job_id: str, owner_id: str) -> ImportJob | None:
    return session.scalar(
        select(ImportJob)
        .where(ImportJob.id == job_id, ImportJob.owner_id == owner_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def get_queued_import_job_for_update(session: Session, job_id: str) -> ImportJob | None:
    return session.scalar(
        select(ImportJob)
        .where(ImportJob.id == job_id, ImportJob.status == ImportJobStatus.QUEUED)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def get_import_job_by_dedupe_key(session: Session, owner_id: str, dedupe_key: str) -> ImportJob | None:
    return session.scalar(select(ImportJob).where(ImportJob.owner_id == owner_id, ImportJob.dedupe_key == dedupe_key))


def count_import_jobs_by_statuses(session: Session, owner_id: str, statuses: set) -> int:
    return len(
        session.scalars(
            select(ImportJob).where(
                ImportJob.owner_id == owner_id,
                ImportJob.status.in_(statuses),
            )
        ).all()
    )
