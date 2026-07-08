from typing import Any

from sqlalchemy.orm.session import Session

from app.imports.error_codes import ImportGeneralErrorCode, ImportRecipeError
from app.imports.events import build_job_event
from app.imports.logging import log_import_failed
from app.models import ImportEventType, ImportJob, ImportJobErrorCode
from app.notifications.notification_data import ImportFailedNotification, build_notification
from app.storage.base import StorageService


def _cleanup_storage_keys(storage: StorageService, storage_keys: list[str]) -> None:
    for storage_key in storage_keys:
        storage.delete(storage_key)


def _parse_error(error: Exception | None) -> tuple[ImportJobErrorCode, str, str, dict[str, Any]]:
    if isinstance(error, ImportRecipeError):
        return error.import_job_code, error.code, error.message, error.extra or {}
    return ImportJobErrorCode.IMPORT_FAILED, ImportGeneralErrorCode.UNEXPECTED_ERROR, str(error) if error else "Import failed.", {}


def process_import_failure(
    job: ImportJob,
    session: Session,
    storage: StorageService,
    saved_storage_keys: list[str],
    error: Exception | None = None,
    cleanup_storage: bool = True,
    **extra: Any,
) -> None:
    if cleanup_storage:
        _cleanup_storage_keys(storage, saved_storage_keys)

    import_job_code, code, message, error_extra = _parse_error(error)
    error_dict = {
        "import_job_code": import_job_code.value,
        "code": code,
        "message": message,
    }

    job.set_failed(import_job_code, code)
    build_job_event(
        job,
        ImportEventType.IMPORT_FAILED,
        error=error_dict,
        **error_extra,
        **extra,
    )
    build_notification(
        session,
        ImportFailedNotification,
        owner_id=job.owner_id,
        entity_id=job.id,
    )
    job_log = job.to_dict()
    session.commit()

    log_import_failed(job_log, error=error_dict, **error_extra, **extra)
