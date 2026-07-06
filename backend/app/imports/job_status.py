from datetime import datetime, timezone

from app.models import ImportJob, ImportJobErrorCode, ImportJobStatus
from app.storage.base import StorageService


def cleanup_storage_keys(storage: StorageService, storage_keys: list[str]) -> None:
    for storage_key in storage_keys:
        storage.delete(storage_key)


def fail_import_job(
    job: ImportJob,
    storage: StorageService,
    saved_storage_keys: list[str],
    error_code: ImportJobErrorCode,
    error_message: str | None,
    *,
    cleanup_storage: bool = True,
) -> None:
    if cleanup_storage:
        cleanup_storage_keys(storage, saved_storage_keys)
    job.status = ImportJobStatus.FAILED
    job.error_code = error_code
    job.error_message = error_message
    job.finished_at = datetime.now(timezone.utc)
