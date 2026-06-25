from pathlib import Path

import pytest

from app.storage.local import LocalStorageService


def test_local_storage_saves_reads_and_deletes_under_root(tmp_path: Path):
    storage = LocalStorageService(tmp_path)

    saved = storage.save(b"hello", original_name="hello.txt", mime_type="text/plain")

    assert saved.storage_key.endswith(".txt")
    assert saved.size_bytes == 5
    assert storage.read(saved.storage_key) == b"hello"

    storage.delete(saved.storage_key)

    with pytest.raises(FileNotFoundError):
        storage.read(saved.storage_key)


def test_local_storage_rejects_path_traversal(tmp_path: Path):
    storage = LocalStorageService(tmp_path)

    with pytest.raises(ValueError, match="storage root"):
        storage.read("../secret.txt")
