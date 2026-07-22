import logging
from collections.abc import Iterable

from app.core.logging import bind_logger
from app.imports.constants import IMPORT_LOG_COMPONENT
from app.storage.base import StorageService
from app.storage.constants import StorageLocation

logger = bind_logger(logging.getLogger(__name__), component=IMPORT_LOG_COMPONENT)


def cleanup_import_storage(
    storage: StorageService,
    location: StorageLocation,
    storage_keys: Iterable[str],
) -> None:
    storage_keys = tuple(storage_keys)
    failed_count = 0
    for storage_key in storage_keys:
        try:
            storage.delete(location, storage_key)
        except Exception as error:
            failed_count += 1
            logger.error(
                "Import storage file cleanup failed.",
                storage_key=storage_key,
                error=repr(error),
            )

    logger.info(
        "Import storage cleanup completed.",
        storage_key_count=len(storage_keys),
        deleted_count=len(storage_keys) - failed_count,
        failed_count=failed_count,
    )
