from app.core.config import Settings


def test_dev_and_preview_default_to_postgres_databases():
    dev = Settings(app_env="dev")
    preview = Settings(app_env="preview")

    assert dev.database_url == "postgresql+psycopg://recipe_manager:recipe_manager@127.0.0.1:5432/recipe_manager_dev"
    assert preview.database_url == "postgresql+psycopg://recipe_manager:recipe_manager@127.0.0.1:5432/recipe_manager_preview"


def test_test_env_defaults_to_sqlite_file():
    settings = Settings(app_env="test")

    assert settings.database_url.endswith("backend\\storage\\test\\app.db") or settings.database_url.endswith("backend/storage/test/app.db")
    assert settings.database_url.startswith("sqlite:///")


def test_max_tags_per_user_defaults_to_50():
    settings = Settings(app_env="test")

    assert settings.max_tags_per_user == 50


def test_recipe_language_defaults_to_ru_and_can_be_configured():
    default_settings = Settings(app_env="test")
    custom_settings = Settings(app_env="test", recipe_language="en")

    assert default_settings.recipe_language == "ru"
    assert custom_settings.recipe_language == "en"


def test_import_retry_settings_have_safe_defaults_and_can_be_configured():
    default_settings = Settings(app_env="test")
    custom_settings = Settings(app_env="test", max_import_attempts=5, import_task_max_retries=2)

    assert default_settings.max_import_attempts == 3
    assert default_settings.import_task_max_retries == 0
    assert custom_settings.max_import_attempts == 5
    assert custom_settings.import_task_max_retries == 2
