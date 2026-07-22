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
        "AWS_REGION",
        "SQS_IMPORTS_QUEUE_URL",
        "SQS_EMBEDDINGS_QUEUE_URL",
        "SQS_ACCOUNT_DELETION_QUEUE_URL",
    ):
        monkeypatch.delenv(variable, raising=False)


def build_sqs_settings(**overrides):
    values = {
        "app_env": AppEnv.PROD,
        "database_url": "postgresql+psycopg://user:pass@db.example.test/app",
        "queue_provider": QueueProvider.SQS,
        "storage_provider": StorageProvider.S3,
        "clerk_secret_key": "test-clerk-secret",
        "aws_region": "eu-west-1",
        "sqs_imports_queue_url": "https://sqs.eu-west-1.amazonaws.com/000000000000/imports",
        "sqs_embeddings_queue_url": "https://sqs.eu-west-1.amazonaws.com/000000000000/embeddings",
        "sqs_account_deletion_queue_url": ("https://sqs.eu-west-1.amazonaws.com/000000000000/account-deletion"),
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


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


def test_preview_dramatiq_does_not_require_aws_queue_settings():
    settings = Settings(
        app_env=AppEnv.PREVIEW,
        clerk_secret_key="test-clerk-secret",
        _env_file=None,
    )

    assert settings.queue_provider is QueueProvider.DRAMATIQ
    assert settings.aws_region is None
    assert settings.sqs_imports_queue_url is None
    assert settings.sqs_embeddings_queue_url is None
    assert settings.sqs_account_deletion_queue_url is None


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
    settings = build_sqs_settings()

    assert settings.queue_provider is QueueProvider.SQS
    assert settings.storage_provider is StorageProvider.S3
    assert settings.redis_url is None
    assert settings.upload_dir is None


@pytest.mark.parametrize(
    ("field_name", "environment_name"),
    [
        ("aws_region", "AWS_REGION"),
        ("sqs_imports_queue_url", "SQS_IMPORTS_QUEUE_URL"),
        ("sqs_embeddings_queue_url", "SQS_EMBEDDINGS_QUEUE_URL"),
        ("sqs_account_deletion_queue_url", "SQS_ACCOUNT_DELETION_QUEUE_URL"),
    ],
)
def test_sqs_provider_requires_all_queue_settings(field_name, environment_name):
    with pytest.raises(ValidationError, match=environment_name):
        build_sqs_settings(**{field_name: None})


def test_sqs_provider_treats_blank_settings_as_missing():
    with pytest.raises(ValidationError, match="AWS_REGION"):
        build_sqs_settings(aws_region="   ")


def test_sqs_provider_requires_distinct_queue_urls():
    shared_url = "https://sqs.eu-west-1.amazonaws.com/000000000000/shared"

    with pytest.raises(ValidationError, match="distinct"):
        build_sqs_settings(
            sqs_imports_queue_url=shared_url,
            sqs_embeddings_queue_url=shared_url,
        )


def test_sqs_provider_accepts_explicit_region_and_distinct_queue_urls():
    settings = build_sqs_settings()

    assert settings.aws_region == "eu-west-1"
    assert settings.sqs_imports_queue_url.endswith("/imports")
    assert settings.sqs_embeddings_queue_url.endswith("/embeddings")
    assert settings.sqs_account_deletion_queue_url.endswith("/account-deletion")


def test_max_tags_per_user_defaults_to_50():
    settings = Settings(app_env=AppEnv.TEST, _env_file=None)

    assert settings.max_tags_per_user == 50


def test_outbox_reconcile_batch_size_defaults_to_one_hundred():
    settings = Settings(app_env=AppEnv.TEST, _env_file=None)

    assert settings.outbox_reconcile_batch_size == 100


def test_maintenance_settings_have_safe_defaults():
    settings = Settings(app_env=AppEnv.TEST, _env_file=None)

    assert settings.maintenance_batch_size == 100
    assert settings.stale_embedding_minutes == 30
    assert settings.stale_recipe_deletion_minutes == 60
    assert settings.stale_account_deletion_minutes == 60


@pytest.mark.parametrize("batch_size", [0, 1001])
def test_maintenance_batch_size_rejects_values_outside_bounds(batch_size):
    with pytest.raises(ValidationError):
        Settings(app_env=AppEnv.TEST, maintenance_batch_size=batch_size, _env_file=None)


@pytest.mark.parametrize(
    "field_name",
    ["stale_embedding_minutes", "stale_recipe_deletion_minutes", "stale_account_deletion_minutes"],
)
def test_maintenance_stale_thresholds_reject_zero(field_name):
    with pytest.raises(ValidationError):
        Settings(app_env=AppEnv.TEST, **{field_name: 0}, _env_file=None)


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


def test_embedding_task_retry_setting_defaults_to_two_and_accepts_zero():
    default_settings = Settings(app_env=AppEnv.TEST, _env_file=None)
    disabled_settings = Settings(app_env=AppEnv.TEST, embedding_task_max_retries=0, _env_file=None)

    assert default_settings.embedding_task_max_retries == 2
    assert disabled_settings.embedding_task_max_retries == 0


def test_embedding_task_retry_setting_rejects_negative_values():
    with pytest.raises(ValidationError, match="embedding_task_max_retries"):
        Settings(app_env=AppEnv.TEST, embedding_task_max_retries=-1, _env_file=None)


def test_account_deletion_task_retry_setting_defaults_to_two_and_accepts_zero():
    default_settings = Settings(app_env=AppEnv.TEST, _env_file=None)
    disabled_settings = Settings(app_env=AppEnv.TEST, account_deletion_task_max_retries=0, _env_file=None)

    assert default_settings.account_deletion_task_max_retries == 2
    assert disabled_settings.account_deletion_task_max_retries == 0


def test_account_deletion_task_retry_setting_rejects_negative_values():
    with pytest.raises(ValidationError, match="account_deletion_task_max_retries"):
        Settings(app_env=AppEnv.TEST, account_deletion_task_max_retries=-1, _env_file=None)


def test_app_env_defaults_to_production_when_environment_is_absent(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    settings = build_sqs_settings(app_env=AppEnv.PROD)

    assert settings.app_env is AppEnv.PROD


def test_clerk_identity_configuration_is_optional_only_in_test():
    assert Settings(app_env=AppEnv.TEST, _env_file=None).clerk_secret_key is None

    with pytest.raises(ValidationError, match="Clerk identity configuration"):
        Settings(app_env=AppEnv.PREVIEW, _env_file=None)

    assert Settings(app_env=AppEnv.PREVIEW, _env_file=None, clerk_secret_key="secret").clerk_secret_key == "secret"


def test_invalid_app_env_is_rejected():
    with pytest.raises(ValidationError):
        Settings(app_env="preview", _env_file=None)
