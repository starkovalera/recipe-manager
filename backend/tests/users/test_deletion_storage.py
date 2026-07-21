from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import AppEnv, Settings
from app.core.infrastructure import QueueProvider, StorageProvider
from app.storage.local import LocalStorageService
from app.users.deletion_storage import get_account_deletion_storage


def test_account_deletion_storage_uses_local_provider_in_preview(tmp_path: Path) -> None:
    settings = Settings(
        app_env=AppEnv.PREVIEW,
        clerk_secret_key="test-clerk-secret",
        upload_dir=tmp_path,
        storage_provider=StorageProvider.LOCAL,
        _env_file=None,
    )

    storage = get_account_deletion_storage(settings)

    assert isinstance(storage, LocalStorageService)
    assert storage.root == tmp_path.resolve()


def test_account_deletion_storage_rejects_s3_until_provider_exists() -> None:
    settings = Settings(
        app_env=AppEnv.PROD,
        database_url="postgresql+psycopg://user:pass@db.example.test/app",
        queue_provider=QueueProvider.SQS,
        storage_provider=StorageProvider.S3,
        aws_region="eu-west-1",
        sqs_imports_queue_url="https://example.test/imports",
        sqs_embeddings_queue_url="https://example.test/embeddings",
        sqs_account_deletion_queue_url="https://example.test/account-deletion",
        clerk_secret_key="test-clerk-secret",
        _env_file=None,
    )

    with pytest.raises(RuntimeError, match="S3.*not implemented"):
        get_account_deletion_storage(settings)


def test_local_account_deletion_storage_requires_upload_dir() -> None:
    settings = SimpleNamespace(
        storage_provider=StorageProvider.LOCAL,
        upload_dir=None,
    )

    with pytest.raises(RuntimeError, match="UPLOAD_DIR"):
        get_account_deletion_storage(settings)
