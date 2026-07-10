from typing import Any

from app.db.session import db_session
from app.imports.constants import TERMINAL_IMPORT_STATUSES
from app.imports.error_codes import ImportGeneralErrorCode, ImportRecipeError
from app.imports.events import build_job_event
from app.imports.logging import log_import_failed
from app.models import ImportEventType, ImportJob, ImportJobErrorCode
from app.notifications.notification_data import ImportFailedNotification, build_notification
from app.storage.base import StorageService


def cleanup_import_storage(storage: StorageService, storage_keys: list[str]) -> None:
    for storage_key in storage_keys:
        storage.delete(storage_key)


def _parse_error(error: Exception | None) -> tuple[ImportJobErrorCode, str, str, dict[str, Any]]:
    if isinstance(error, ImportRecipeError):
        return error.import_job_code, error.code, error.message, error.extra or {}
    return ImportJobErrorCode.IMPORT_FAILED, ImportGeneralErrorCode.UNEXPECTED_ERROR, str(error) if error else "Import failed.", {}


def process_import_failure(
    job_id: str,
    storage: StorageService,
    saved_storage_keys: list[str],
    error: Exception | None = None,
    cleanup_storage: bool = True,
) -> None:
    if cleanup_storage:
        cleanup_import_storage(storage, saved_storage_keys)

    with db_session() as session:
        job = session.get(ImportJob, job_id)
        if job is None or job.status in TERMINAL_IMPORT_STATUSES:
            return

        import_job_code, code, message, error_extra = _parse_error(error)
        error_dict = {
            "import_job_code": import_job_code.value,
            "code": code,
            "message": message,
        }

        job.set_failed(import_job_code, code)
        build_job_event(
            session,
            import_job_id=job.id,
            event_type=ImportEventType.IMPORT_FAILED,
            error=error_dict,
            **error_extra,
        )
        build_notification(
            session,
            ImportFailedNotification,
            owner_id=job.owner_id,
            entity_id=job.id,
        )
        session.flush()
        session.refresh(job)

        log_import_failed(job, error=error_dict, **error_extra)
