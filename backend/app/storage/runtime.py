from collections.abc import Mapping

from app.core.config import Settings, get_settings
from app.core.infrastructure import StorageProvider
from app.storage.base import StorageService
from app.storage.constants import StorageLocation
from app.storage.errors import StorageConfigurationError
from app.storage.local import LocalStorageService
from app.storage.s3 import S3StorageService
from app.storage.types import StorageLocator


def get_storage_location_to_locator(
    settings: Settings,
) -> Mapping[StorageLocation, StorageLocator]:
    if settings.storage_provider is StorageProvider.LOCAL:
        if settings.upload_dir is None:
            raise StorageConfigurationError("UPLOAD_DIR is required for local storage.")
        if settings.system_artifacts_dir is None:
            raise StorageConfigurationError("SYSTEM_ARTIFACTS_DIR is required for local storage.")
        return {
            StorageLocation.USER_MEDIA: settings.upload_dir,
            StorageLocation.SYSTEM_ARTIFACTS: settings.system_artifacts_dir,
        }

    if settings.storage_provider is StorageProvider.S3:
        if not settings.s3_user_media_bucket_name:
            raise StorageConfigurationError("S3_USER_MEDIA_BUCKET_NAME is required for S3 storage.")
        if not settings.s3_system_artifacts_bucket_name:
            raise StorageConfigurationError("S3_SYSTEM_ARTIFACTS_BUCKET_NAME is required for S3 storage.")
        return {
            StorageLocation.USER_MEDIA: settings.s3_user_media_bucket_name,
            StorageLocation.SYSTEM_ARTIFACTS: settings.s3_system_artifacts_bucket_name,
        }

    raise StorageConfigurationError("Storage provider is not configured.")


def get_storage_service(settings: Settings | None = None) -> StorageService:
    resolved_settings = settings or get_settings()

    if resolved_settings.storage_provider is StorageProvider.LOCAL:
        location_to_locator = get_storage_location_to_locator(resolved_settings)
        return LocalStorageService(location_to_locator=location_to_locator)

    if resolved_settings.storage_provider is StorageProvider.S3:
        if not resolved_settings.aws_region:
            raise StorageConfigurationError("AWS_REGION is required for S3 storage.")
        return S3StorageService(
            location_to_locator=get_storage_location_to_locator(resolved_settings),
            region_name=resolved_settings.aws_region,
        )

    raise StorageConfigurationError("Storage provider is not configured.")
