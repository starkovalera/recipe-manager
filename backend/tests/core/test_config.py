import pytest
from pydantic import ValidationError

from app.core.config import AppEnv, Settings


def test_dev_and_preview_default_to_postgres_databases():
    clerk = {"clerk_secret_key": "secret"}
    dev = Settings(app_env=AppEnv.DEV, **clerk)
    preview = Settings(app_env=AppEnv.PREVIEW, **clerk)

    assert dev.database_url == "postgresql+psycopg://recipe_manager:recipe_manager@127.0.0.1:5432/recipe_manager_dev"
    assert preview.database_url == "postgresql+psycopg://recipe_manager:recipe_manager@127.0.0.1:5432/recipe_manager_preview"


def test_test_env_defaults_to_sqlite_file():
    settings = Settings(app_env=AppEnv.TEST)

    assert settings.database_url.endswith("backend\\storage\\test\\app.db") or settings.database_url.endswith("backend/storage/test/app.db")
    assert settings.database_url.startswith("sqlite:///")


def test_max_tags_per_user_defaults_to_50():
    settings = Settings(app_env=AppEnv.TEST)

    assert settings.max_tags_per_user == 50


def test_recipe_language_defaults_to_ru_and_can_be_configured():
    default_settings = Settings(app_env=AppEnv.TEST)
    custom_settings = Settings(app_env=AppEnv.TEST, recipe_language="en")

    assert default_settings.recipe_language == "ru"
    assert custom_settings.recipe_language == "en"


def test_import_retry_settings_have_safe_defaults_and_can_be_configured():
    default_settings = Settings(app_env=AppEnv.TEST)
    custom_settings = Settings(app_env=AppEnv.TEST, max_import_attempts=5, import_task_max_retries=2)

    assert default_settings.max_import_attempts == 3
    assert default_settings.import_task_max_retries == 0
    assert custom_settings.max_import_attempts == 5
    assert custom_settings.import_task_max_retries == 2


def test_app_env_defaults_to_production_when_environment_is_absent(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    settings = Settings(_env_file=None, clerk_secret_key="secret")

    assert settings.app_env is AppEnv.PROD


def test_clerk_identity_configuration_is_optional_only_in_test():
    assert Settings(app_env=AppEnv.TEST, _env_file=None).clerk_secret_key is None

    with pytest.raises(ValidationError, match="Clerk identity configuration"):
        Settings(app_env=AppEnv.PREVIEW, _env_file=None)

    assert Settings(app_env=AppEnv.PREVIEW, _env_file=None, clerk_secret_key="secret").clerk_secret_key == "secret"


def test_invalid_app_env_is_rejected():
    with pytest.raises(ValidationError):
        Settings(app_env="preview", _env_file=None)
