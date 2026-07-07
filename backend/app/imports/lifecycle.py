from sqlalchemy.orm import Session

from app.imports.events import record_job_event
from app.models import ImportEventType, ImportJob, ImportJobStatus
from app.services.notifications import create_notification


def handle_import_started(session: Session, job: ImportJob, *, client_import_id: str, dedupe_key: str) -> None:
    record_job_event(job, ImportEventType.IMPORT_CREATED, {"clientImportId": client_import_id, "dedupeKey": dedupe_key})
    create_notification(
        session,
        owner_id=job.owner_id,
        type="import_started",
        title="Import started",
        message="Recipe import started.",
        entity_type="import_job",
        entity_id=job.id,
    )


def handle_import_failed(session: Session, job: ImportJob, *, payload: dict | None = None) -> None:
    event_payload = {
        "error_code": job.error_code.value if job.error_code is not None else None,
        "error_message": job.error_message,
        **(payload or {}),
    }
    record_job_event(job, ImportEventType.IMPORT_FAILED, event_payload)
    create_notification(
        session,
        owner_id=job.owner_id,
        type="import_failed",
        title="Import failed",
        message=job.error_message or "Recipe import failed.",
        entity_type="import_job",
        entity_id=job.id,
    )


def handle_recipe_created(session: Session, job: ImportJob, *, recipe_id: str, status: ImportJobStatus) -> None:
    record_job_event(job, ImportEventType.RECIPE_CREATED, {"recipeId": recipe_id, "status": status.value})
    if status == ImportJobStatus.SUCCEEDED_WITH_FLAGS:
        notification_type = "import_succeeded_with_flags"
        title = "Import completed with warning"
        message = "Recipe import completed and needs review."
    else:
        notification_type = "import_succeeded"
        title = "Import completed"
        message = "Recipe import completed."
    create_notification(
        session,
        owner_id=job.owner_id,
        type=notification_type,
        title=title,
        message=message,
        entity_type="recipe",
        entity_id=recipe_id,
    )
