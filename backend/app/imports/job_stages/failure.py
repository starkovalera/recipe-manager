from app.db.session import db_session
from app.imports.constants import TERMINAL_IMPORT_STATUSES
from app.imports.error_policy import classify_import_error
from app.imports.events import build_job_event
from app.imports.logging import log_import_failed
from app.imports.outcomes import ImportProcessingDisposition, ImportProcessingResult
from app.imports.storage_cleanup import cleanup_import_storage
from app.models import ImportEventType, ImportJob
from app.notifications.notification_data import ImportFailedNotification, build_notification
from app.storage.base import StorageService
from app.storage.constants import StorageLocation


def process_import_failure(
    job_id: str,
    storage: StorageService,
    primary_storage_keys: list[str],
    secondary_storage_keys: list[str],
    max_import_attempts: int,
    error: Exception | None = None,
    cleanup_storage: bool = True,
) -> ImportProcessingResult:
    with db_session() as session:
        job = session.get(ImportJob, job_id)
        if job is None or job.status in TERMINAL_IMPORT_STATUSES:
            return ImportProcessingResult(
                import_job_id=job_id,
                disposition=ImportProcessingDisposition.NOOP,
            )

        classified = classify_import_error(error)
        retryable = classified.policy.automatic_retry
        terminal = not retryable or job.attempt_count >= max_import_attempts
        error_dict = {
            "import_job_code": classified.policy.import_job_error_code.value,
            "code": classified.detailed_code,
            "message": classified.message,
        }

        if terminal:
            job.set_failed(
                classified.policy.import_job_error_code,
                classified.detailed_code,
            )
            build_notification(
                session,
                ImportFailedNotification,
                owner_id=job.owner_id,
                entity_id=job.id,
            )
            disposition = ImportProcessingDisposition.PERMANENT_FAILURE
        else:
            job.set_queued_for_retry()
            disposition = ImportProcessingDisposition.RETRYABLE_FAILURE

        build_job_event(
            session,
            import_job_id=job.id,
            event_type=ImportEventType.IMPORT_FAILED,
            error=error_dict,
            retryable=retryable,
            terminal=terminal,
            attempt_count=job.attempt_count,
            max_attempts=max_import_attempts,
            **classified.extra,
        )
        session.flush()
        session.refresh(job)

    log_payload = {
        "error": error_dict,
        "retryable": retryable,
        "terminal": terminal,
        "attempt_count": job.attempt_count,
        "max_attempts": max_import_attempts,
        **classified.extra,
    }
    try:
        log_import_failed(job, **log_payload)
    except Exception:
        pass

    if cleanup_storage:
        cleanup_import_storage(storage, StorageLocation.USER_MEDIA, secondary_storage_keys)
        if terminal:
            cleanup_import_storage(storage, StorageLocation.USER_MEDIA, primary_storage_keys)

    return ImportProcessingResult(
        import_job_id=job_id,
        disposition=disposition,
        detailed_error_code=classified.detailed_code,
    )
