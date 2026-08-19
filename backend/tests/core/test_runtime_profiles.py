from pathlib import Path
from unittest.mock import Mock

import pytest

from app.core.config import AppEnv, Settings
from app.core.runtime import prepare_runtime
from app.main import prepare_application_runtime

CLERK_SETTINGS = {"clerk_secret_key": "secret"}


def test_production_application_startup_does_not_prepare_local_state_or_run_migrations(monkeypatch):
    settings = Mock(app_env=AppEnv.PROD, database_url="postgresql+psycopg://production", upload_dir=None)
    prepare = Mock()
    migrate = Mock()
    monkeypatch.setattr("app.main.prepare_runtime", prepare)
    monkeypatch.setattr("app.main.run_migrations", migrate)

    prepare_application_runtime(settings)

    prepare.assert_not_called()
    migrate.assert_not_called()


def test_non_production_application_startup_keeps_runtime_preparation_and_migrations(monkeypatch):
    settings = Mock(app_env=AppEnv.DEV, database_url="sqlite:///dev.db")
    prepare = Mock()
    migrate = Mock()
    reset = Mock()
    monkeypatch.setattr("app.main.prepare_runtime", prepare)
    monkeypatch.setattr("app.main.run_migrations", migrate)
    monkeypatch.setattr("app.main.reset_database_schema", reset)

    prepare_application_runtime(settings)

    prepare.assert_called_once_with(settings, reset_database=reset)
    migrate.assert_called_once_with("sqlite:///dev.db")


def test_dev_runtime_does_not_delete_existing_files(tmp_path: Path):
    db_path = tmp_path / "dev" / "app.db"
    upload_dir = tmp_path / "dev" / "uploads"
    upload_dir.mkdir(parents=True)
    db_path.write_text("db", encoding="utf-8")
    saved = upload_dir / "saved.txt"
    saved.write_text("keep", encoding="utf-8")
    settings = Settings(app_env=AppEnv.DEV, database_url=f"sqlite:///{db_path}", upload_dir=upload_dir, **CLERK_SETTINGS)

    prepare_runtime(settings)

    assert db_path.read_text(encoding="utf-8") == "db"
    assert saved.read_text(encoding="utf-8") == "keep"


def test_preview_runtime_deletes_only_preview_storage(tmp_path: Path):
    preview_root = tmp_path / "storage" / "preview"
    db_path = preview_root / "app.db"
    upload_dir = preview_root / "uploads"
    upload_dir.mkdir(parents=True)
    db_path.write_text("db", encoding="utf-8")
    saved = upload_dir / "saved.txt"
    saved.write_text("delete", encoding="utf-8")
    settings = Settings(app_env=AppEnv.PREVIEW, database_url=f"sqlite:///{db_path}", upload_dir=upload_dir, **CLERK_SETTINGS)

    prepare_runtime(settings)

    assert not db_path.exists()
    assert upload_dir.exists()
    assert list(upload_dir.iterdir()) == []


def test_preview_runtime_refuses_paths_outside_preview_storage(tmp_path: Path):
    unsafe_upload_dir = tmp_path / "storage" / "dev" / "uploads"
    unsafe_upload_dir.mkdir(parents=True)
    settings = Settings(
        app_env=AppEnv.PREVIEW,
        database_url=f"sqlite:///{tmp_path / 'storage' / 'dev' / 'app.db'}",
        upload_dir=unsafe_upload_dir,
        **CLERK_SETTINGS,
    )

    with pytest.raises(RuntimeError, match="preview"):
        prepare_runtime(settings)


def test_preview_runtime_resets_postgres_state_and_uploads(tmp_path: Path):
    preview_root = tmp_path / "storage" / "preview"
    upload_dir = preview_root / "uploads"
    upload_dir.mkdir(parents=True)
    saved = upload_dir / "saved.txt"
    saved.write_text("delete", encoding="utf-8")
    reset_calls: list[str] = []
    settings = Settings(
        app_env=AppEnv.PREVIEW,
        database_url="postgresql+psycopg://recipe:recipe@127.0.0.1:5432/recipe_manager_preview",
        upload_dir=upload_dir,
        **CLERK_SETTINGS,
    )

    prepare_runtime(settings, reset_database=lambda database_url: reset_calls.append(database_url))

    assert reset_calls == ["postgresql+psycopg://recipe:recipe@127.0.0.1:5432/recipe_manager_preview"]
    assert upload_dir.exists()
    assert list(upload_dir.iterdir()) == []


def test_preview_runtime_requires_reset_hook_for_postgres(tmp_path: Path):
    preview_root = tmp_path / "storage" / "preview"
    upload_dir = preview_root / "uploads"
    upload_dir.mkdir(parents=True)
    settings = Settings(
        app_env=AppEnv.PREVIEW,
        database_url="postgresql+psycopg://recipe:recipe@127.0.0.1:5432/recipe_manager_preview",
        upload_dir=upload_dir,
        **CLERK_SETTINGS,
    )

    with pytest.raises(RuntimeError, match="reset"):
        prepare_runtime(settings)
