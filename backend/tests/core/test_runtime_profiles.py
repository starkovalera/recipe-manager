from pathlib import Path

import pytest

from app.core.config import AppEnv, Settings
from app.core.runtime import prepare_runtime

CLERK_SETTINGS = {"clerk_secret_key": "secret"}


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
