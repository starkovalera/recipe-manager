from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.errors import (
    ActiveImportExistsError,
    ImportAttemptsExhaustedError,
    ImportNotFoundError,
    ImportNotRetryableError,
)
from app.db.session import db_transaction
from app.imports.constants import ACTIVE_IMPORT_STATUSES
from app.imports.queries import count_import_jobs_by_statuses, get_import_job_for_update
from app.models import ImportJob, ImportJobStatus, Notification
from app.notifications.notification_data import ImportStartedNotification, build_notification


@dataclass(frozen=True)
class ImportRetryResult:
    job: ImportJob
    notification_id: str


def request_import_retry(
    session: Session,
    *,
    job_id: str,
    owner_id: str,
    max_import_attempts: int,
    max_parallel_imports: int,
) -> ImportRetryResult:
    with db_transaction(session):
        job = get_import_job_for_update(session, job_id, owner_id)
        if job is None:
            raise ImportNotFoundError()
        if job.status != ImportJobStatus.FAILED:
            raise ImportNotRetryableError()
        if job.attempt_count >= max_import_attempts:
            raise ImportAttemptsExhaustedError(max_attempts=max_import_attempts)

        active_import_count = count_import_jobs_by_statuses(session, owner_id, ACTIVE_IMPORT_STATUSES)
        if active_import_count >= max_parallel_imports:
            raise ActiveImportExistsError(max_active_imports=max_parallel_imports)

        job.status = ImportJobStatus.QUEUED
        notification = build_notification(
            session,
            ImportStartedNotification,
            owner_id=job.owner_id,
            entity_id=job.id,
        )
        session.flush()
        session.refresh(job)
        return ImportRetryResult(job=job, notification_id=notification.id)


def compensate_import_retry_publish_failure(
    session: Session,
    *,
    job_id: str,
    owner_id: str,
    notification_id: str,
) -> tuple[ImportJob, bool]:
    with db_transaction(session):
        job = get_import_job_for_update(session, job_id, owner_id)
        if job is None:
            raise ImportNotFoundError()
        if job.status != ImportJobStatus.QUEUED:
            return job, False

        job.status = ImportJobStatus.FAILED
        notification = session.get(Notification, notification_id)
        if notification is not None:
            session.delete(notification)
        session.flush()
        session.refresh(job)
        return job, True
