from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import ImportJob, ImportJobStatus


def list_internal_import_jobs(session: Session, *, owner_id: str | None = None) -> list[ImportJob]:
    statement = (
        select(ImportJob).options(selectinload(ImportJob.sources), selectinload(ImportJob.events)).order_by(ImportJob.created_at.desc())
    )
    if owner_id is not None:
        statement = statement.where(ImportJob.owner_id == owner_id)
    return list(session.scalars(statement))


def get_import_job_unscoped(session: Session, job_id: str) -> ImportJob | None:
    return session.get(ImportJob, job_id)


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
