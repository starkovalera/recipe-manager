from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import AppEnv, Settings
from app.core.infrastructure import QueueProvider, StorageProvider
from app.storage.constants import StorageLocation
from app.storage.errors import StorageConfigurationError
from app.storage.local import LocalStorageService
from app.storage.runtime import get_storage_location_to_locator, get_storage_service


def test_storage_service_uses_local_provider_in_preview(tmp_path: Path) -> None:
    settings = Settings(
        app_env=AppEnv.PREVIEW,
        clerk_secret_key="test-clerk-secret",
        upload_dir=tmp_path,
        storage_provider=StorageProvider.LOCAL,
        _env_file=None,
    )

    storage = get_storage_service(settings)

    assert isinstance(storage, LocalStorageService)
    assert storage.path_for_response(StorageLocation.USER_MEDIA, "file.jpg").parent == tmp_path.resolve()


def test_storage_service_rejects_s3_until_provider_exists() -> None:
    settings = Settings(
        app_env=AppEnv.PROD,
        database_url="postgresql+psycopg://user:pass@db.example.test/app",
        queue_provider=QueueProvider.SQS,
        storage_provider=StorageProvider.S3,
        aws_region="eu-west-1",
        s3_user_media_bucket_name="recipe-manager-test-user-media",
        sqs_imports_queue_url="https://example.test/imports",
        sqs_embeddings_queue_url="https://example.test/embeddings",
        sqs_account_deletion_queue_url="https://example.test/account-deletion",
        clerk_secret_key="test-clerk-secret",
        _env_file=None,
    )

    with pytest.raises(RuntimeError, match="S3.*not implemented"):
        get_storage_service(settings)


def test_local_storage_service_requires_upload_dir() -> None:
    settings = SimpleNamespace(
        storage_provider=StorageProvider.LOCAL,
        upload_dir=None,
    )

    with pytest.raises(StorageConfigurationError, match="UPLOAD_DIR"):
        get_storage_location_to_locator(settings)


def test_local_storage_location_maps_to_path(tmp_path: Path) -> None:
    settings = SimpleNamespace(
        storage_provider=StorageProvider.LOCAL,
        upload_dir=tmp_path,
        s3_user_media_bucket_name=None,
    )

    assert get_storage_location_to_locator(settings) == {
        StorageLocation.USER_MEDIA: tmp_path,
    }


def test_s3_storage_location_maps_to_bucket_name() -> None:
    settings = SimpleNamespace(
        storage_provider=StorageProvider.S3,
        upload_dir=None,
        s3_user_media_bucket_name="recipe-manager-test-user-media",
    )

    assert get_storage_location_to_locator(settings) == {
        StorageLocation.USER_MEDIA: "recipe-manager-test-user-media",
    }


def test_storage_location_mapping_rejects_unconfigured_provider() -> None:
    settings = SimpleNamespace(
        storage_provider=None,
        upload_dir=None,
        s3_user_media_bucket_name=None,
    )

    with pytest.raises(StorageConfigurationError, match="provider"):
        get_storage_location_to_locator(settings)
