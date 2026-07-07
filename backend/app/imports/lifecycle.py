from sqlalchemy.orm import Session

from app.imports.events import build_job_event
from app.models import ImportEventType, ImportJob, ImportJobStatus
from app.notifications.notification_data import (
    ImportFailedNotification,
    ImportStartedNotification,
    ImportSucceededNotification,
    ImportSucceededWithFlagsNotification,
    build_notification,
)


def handle_import_started(session: Session, job: ImportJob, *, client_import_id: str, dedupe_key: str) -> None:
    build_job_event(job, ImportEventType.IMPORT_CREATED, client_import_id=client_import_id, dedupe_key=dedupe_key)
    build_notification(
        session,
        ImportStartedNotification,
        owner_id=job.owner_id,
        entity_id=job.id,
    )


def handle_import_failed(session: Session, job: ImportJob, *, payload: dict | None = None) -> None:
    build_job_event(job, ImportEventType.IMPORT_FAILED, **(payload or {}))
    build_notification(
        session,
        ImportFailedNotification,
        owner_id=job.owner_id,
        entity_id=job.id,
    )


def handle_recipe_created(session: Session, job: ImportJob, *, recipe_id: str, status: ImportJobStatus) -> None:
    build_job_event(job, ImportEventType.RECIPE_CREATED, recipe_id=recipe_id, status=status.value)
    if status == ImportJobStatus.SUCCEEDED_WITH_FLAGS:
        notification_cls = ImportSucceededWithFlagsNotification
    else:
        notification_cls = ImportSucceededNotification
    build_notification(
        session,
        notification_cls,
        owner_id=job.owner_id,
        entity_id=recipe_id,
    )
