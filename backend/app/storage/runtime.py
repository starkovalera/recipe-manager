from app.core.config import Settings, get_settings
from app.core.infrastructure import StorageProvider
from app.storage.base import StorageService
from app.storage.local import LocalStorageService


def get_storage_service(settings: Settings | None = None) -> StorageService:
    resolved_settings = settings or get_settings()

    if resolved_settings.storage_provider is StorageProvider.LOCAL:
        if resolved_settings.upload_dir is None:
            raise RuntimeError("UPLOAD_DIR is required for local storage.")
        return LocalStorageService(resolved_settings.upload_dir)

    if resolved_settings.storage_provider is StorageProvider.S3:
        raise RuntimeError("S3 storage is not implemented yet.")

    raise RuntimeError("Storage provider is not configured.")
