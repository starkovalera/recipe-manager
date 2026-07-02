from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import ImportJob


def list_internal_import_jobs(session: Session) -> list[ImportJob]:
    return session.scalars(
        select(ImportJob)
        .options(selectinload(ImportJob.sources), selectinload(ImportJob.events))
        .order_by(ImportJob.created_at.desc())
    ).all()


def get_import_job(session: Session, job_id: str, owner_id: str) -> ImportJob | None:
    return session.scalar(select(ImportJob).where(ImportJob.id == job_id, ImportJob.owner_id == owner_id))


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
