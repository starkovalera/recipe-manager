from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import AppEnv, Settings
from app.core.infrastructure import QueueProvider, StorageProvider


@pytest.fixture(autouse=True)
def clear_infrastructure_environment(monkeypatch):
    for variable in (
        "APP_ENV",
        "DATABASE_URL",
        "QUEUE_PROVIDER",
        "STORAGE_PROVIDER",
        "REDIS_URL",
        "UPLOAD_DIR",
    ):
        monkeypatch.delenv(variable, raising=False)


def test_dev_and_preview_default_to_postgres_databases():
    clerk = {"clerk_secret_key": "secret"}
    dev = Settings(app_env=AppEnv.DEV, _env_file=None, **clerk)
    preview = Settings(app_env=AppEnv.PREVIEW, _env_file=None, **clerk)

    assert dev.database_url == "postgresql+psycopg://recipe_manager:recipe_manager@127.0.0.1:5432/recipe_manager_dev"
    assert preview.database_url == "postgresql+psycopg://recipe_manager:recipe_manager@127.0.0.1:5432/recipe_manager_preview"
    assert dev.queue_provider is QueueProvider.DRAMATIQ
    assert dev.storage_provider is StorageProvider.LOCAL


def test_preview_uses_local_infrastructure_defaults():
    settings = Settings(app_env=AppEnv.PREVIEW, clerk_secret_key="secret", _env_file=None)

    assert settings.database_url == "postgresql+psycopg://recipe_manager:recipe_manager@127.0.0.1:5432/recipe_manager_preview"
    assert settings.queue_provider is QueueProvider.DRAMATIQ
    assert settings.storage_provider is StorageProvider.LOCAL
    assert settings.redis_url == "redis://127.0.0.1:6379/0"
    assert settings.upload_dir is not None
    assert settings.upload_dir == Path(__file__).resolve().parents[2] / "storage" / "preview" / "uploads"


def test_test_env_defaults_to_sqlite_file():
    settings = Settings(app_env=AppEnv.TEST, _env_file=None)

    assert settings.database_url.endswith("backend\\storage\\test\\app.db") or settings.database_url.endswith("backend/storage/test/app.db")
    assert settings.database_url.startswith("sqlite:///")
    assert settings.queue_provider is QueueProvider.DRAMATIQ
    assert settings.storage_provider is StorageProvider.LOCAL
    assert settings.upload_dir is not None


def test_prod_rejects_missing_database_url():
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(
            app_env=AppEnv.PROD,
            queue_provider=QueueProvider.SQS,
            storage_provider=StorageProvider.S3,
            clerk_secret_key="secret",
            _env_file=None,
        )


def test_prod_rejects_sqlite_database():
    with pytest.raises(ValidationError, match="PostgreSQL"):
        Settings(
            app_env=AppEnv.PROD,
            database_url="sqlite:///production.db",
            queue_provider=QueueProvider.SQS,
            storage_provider=StorageProvider.S3,
            clerk_secret_key="secret",
            _env_file=None,
        )


def test_prod_rejects_dramatiq():
    with pytest.raises(ValidationError, match="SQS"):
        Settings(
            app_env=AppEnv.PROD,
            database_url="postgresql+psycopg://user:pass@db.example.test/app",
            queue_provider=QueueProvider.DRAMATIQ,
            storage_provider=StorageProvider.S3,
            clerk_secret_key="secret",
            _env_file=None,
        )


def test_prod_rejects_local_storage():
    with pytest.raises(ValidationError, match="S3"):
        Settings(
            app_env=AppEnv.PROD,
            database_url="postgresql+psycopg://user:pass@db.example.test/app",
            queue_provider=QueueProvider.SQS,
            storage_provider=StorageProvider.LOCAL,
            clerk_secret_key="secret",
            _env_file=None,
        )


def test_prod_rejects_redis_url():
    with pytest.raises(ValidationError, match="REDIS_URL"):
        Settings(
            app_env=AppEnv.PROD,
            database_url="postgresql+psycopg://user:pass@db.example.test/app",
            queue_provider=QueueProvider.SQS,
            storage_provider=StorageProvider.S3,
            redis_url="redis://redis.example.test:6379/0",
            clerk_secret_key="secret",
            _env_file=None,
        )


def test_prod_rejects_upload_dir(tmp_path):
    with pytest.raises(ValidationError, match="UPLOAD_DIR"):
        Settings(
            app_env=AppEnv.PROD,
            database_url="postgresql+psycopg://user:pass@db.example.test/app",
            queue_provider=QueueProvider.SQS,
            storage_provider=StorageProvider.S3,
            upload_dir=tmp_path / "uploads",
            clerk_secret_key="secret",
            _env_file=None,
        )


def test_prod_accepts_explicit_target_providers():
    settings = Settings(
        app_env=AppEnv.PROD,
        database_url="postgresql+psycopg://user:pass@db.example.test/app",
        queue_provider=QueueProvider.SQS,
        storage_provider=StorageProvider.S3,
        clerk_secret_key="secret",
        _env_file=None,
    )

    assert settings.queue_provider is QueueProvider.SQS
    assert settings.storage_provider is StorageProvider.S3
    assert settings.redis_url is None
    assert settings.upload_dir is None


def test_max_tags_per_user_defaults_to_50():
    settings = Settings(app_env=AppEnv.TEST, _env_file=None)

    assert settings.max_tags_per_user == 50


def test_outbox_reconcile_batch_size_defaults_to_one_hundred():
    settings = Settings(app_env=AppEnv.TEST, _env_file=None)

    assert settings.outbox_reconcile_batch_size == 100


@pytest.mark.parametrize("batch_size", [0, 1001])
def test_outbox_reconcile_batch_size_rejects_values_outside_bounds(batch_size):
    with pytest.raises(ValidationError):
        Settings(
            app_env=AppEnv.TEST,
            outbox_reconcile_batch_size=batch_size,
            _env_file=None,
        )


def test_recipe_language_defaults_to_ru_and_can_be_configured():
    default_settings = Settings(app_env=AppEnv.TEST, _env_file=None)
    custom_settings = Settings(app_env=AppEnv.TEST, recipe_language="en", _env_file=None)

    assert default_settings.recipe_language == "ru"
    assert custom_settings.recipe_language == "en"


def test_import_retry_settings_have_safe_defaults_and_can_be_configured():
    default_settings = Settings(app_env=AppEnv.TEST, _env_file=None)
    custom_settings = Settings(app_env=AppEnv.TEST, max_import_attempts=5, import_task_max_retries=2, _env_file=None)

    assert default_settings.max_import_attempts == 3
    assert default_settings.import_task_max_retries == 0
    assert custom_settings.max_import_attempts == 5
    assert custom_settings.import_task_max_retries == 2


def test_app_env_defaults_to_production_when_environment_is_absent(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    settings = Settings(
        database_url="postgresql+psycopg://user:pass@db.example.test/app",
        queue_provider=QueueProvider.SQS,
        storage_provider=StorageProvider.S3,
        clerk_secret_key="secret",
        _env_file=None,
    )

    assert settings.app_env is AppEnv.PROD


def test_clerk_identity_configuration_is_optional_only_in_test():
    assert Settings(app_env=AppEnv.TEST, _env_file=None).clerk_secret_key is None

    with pytest.raises(ValidationError, match="Clerk identity configuration"):
        Settings(app_env=AppEnv.PREVIEW, _env_file=None)

    assert Settings(app_env=AppEnv.PREVIEW, _env_file=None, clerk_secret_key="secret").clerk_secret_key == "secret"


def test_invalid_app_env_is_rejected():
    with pytest.raises(ValidationError):
        Settings(app_env="preview", _env_file=None)
