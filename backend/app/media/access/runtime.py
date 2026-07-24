from typing import cast

from app.core.config import Settings, get_settings
from app.core.infrastructure import StorageProvider
from app.media.access.local import LocalDownloadAccessProvider
from app.media.access.s3 import S3DownloadAccessProvider
from app.media.access.types import DownloadAccessProvider
from app.storage.local import LocalStorageService
from app.storage.runtime import get_storage_service


def get_download_access_provider(settings: Settings | None = None) -> DownloadAccessProvider:
    resolved_settings = settings or get_settings()
    if resolved_settings.storage_provider is StorageProvider.LOCAL:
        storage = cast(LocalStorageService, get_storage_service(resolved_settings))
        return LocalDownloadAccessProvider(storage)
    if resolved_settings.storage_provider is StorageProvider.S3:
        return S3DownloadAccessProvider(
            bucket_name=resolved_settings.s3_user_media_bucket_name or "",
            region_name=resolved_settings.aws_region or "",
        )
    raise RuntimeError("Unsupported media access provider.")
