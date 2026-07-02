from datetime import datetime, timezone
from typing import Protocol

from app.core.errors import ErrorCode
from app.models import ImportJob, ImportJobStatus


class StorageCleaner(Protocol):
    def delete(self, storage_key: str) -> None: ...


def cleanup_storage_keys(storage: StorageCleaner, storage_keys: list[str]) -> None:
    for storage_key in storage_keys:
        storage.delete(storage_key)


def fail_import_job(
    job: ImportJob,
    storage: StorageCleaner,
    saved_storage_keys: list[str],
    error_code: ErrorCode,
    error_message: str,
) -> None:
    cleanup_storage_keys(storage, saved_storage_keys)
    job.status = ImportJobStatus.FAILED
    job.error_code = error_code.value
    job.error_message = error_message
    job.finished_at = datetime.now(timezone.utc)
