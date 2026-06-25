from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.runtime import prepare_runtime


def test_dev_runtime_does_not_delete_existing_files(tmp_path: Path):
    db_path = tmp_path / "dev" / "app.db"
    upload_dir = tmp_path / "dev" / "uploads"
    upload_dir.mkdir(parents=True)
    db_path.write_text("db", encoding="utf-8")
    saved = upload_dir / "saved.txt"
    saved.write_text("keep", encoding="utf-8")
    settings = Settings(app_env="dev", database_url=f"sqlite:///{db_path}", upload_dir=upload_dir)

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
    settings = Settings(app_env="preview", database_url=f"sqlite:///{db_path}", upload_dir=upload_dir)

    prepare_runtime(settings)

    assert not db_path.exists()
    assert upload_dir.exists()
    assert list(upload_dir.iterdir()) == []


def test_preview_runtime_refuses_paths_outside_preview_storage(tmp_path: Path):
    unsafe_upload_dir = tmp_path / "storage" / "dev" / "uploads"
    unsafe_upload_dir.mkdir(parents=True)
    settings = Settings(
        app_env="preview",
        database_url=f"sqlite:///{tmp_path / 'storage' / 'dev' / 'app.db'}",
        upload_dir=unsafe_upload_dir,
    )

    with pytest.raises(RuntimeError, match="preview"):
        prepare_runtime(settings)
