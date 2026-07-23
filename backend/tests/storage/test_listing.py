import os
from datetime import timezone
from pathlib import Path

import pytest

from app.storage.constants import StorageLocation
from app.storage.local import LocalStorageService


def build_storage(tmp_path: Path) -> LocalStorageService:
    return LocalStorageService(
        location_to_locator={
            StorageLocation.USER_MEDIA: tmp_path / "uploads",
            StorageLocation.SYSTEM_ARTIFACTS: tmp_path / "system-artifacts",
        }
    )


@pytest.mark.parametrize("limit", [0, -1, 1001])
def test_list_objects_rejects_invalid_limit(tmp_path: Path, limit: int) -> None:
    with pytest.raises(ValueError, match="limit"):
        build_storage(tmp_path).list_objects(StorageLocation.USER_MEDIA, prefix="imports/source/", limit=limit)


@pytest.mark.parametrize("prefix", ["/absolute", "../outside", "nested/../../outside"])
def test_list_objects_rejects_unsafe_prefix(tmp_path: Path, prefix: str) -> None:
    with pytest.raises(ValueError, match="prefix"):
        build_storage(tmp_path).list_objects(StorageLocation.USER_MEDIA, prefix=prefix, limit=10)


@pytest.mark.skipif(os.name != "nt", reason="Windows path semantics are runtime-specific.")
def test_list_objects_rejects_windows_absolute_prefix_on_windows(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="prefix"):
        build_storage(tmp_path).list_objects(StorageLocation.USER_MEDIA, prefix="C:\\absolute", limit=10)


@pytest.mark.skipif(os.name == "nt", reason="POSIX path semantics are runtime-specific.")
def test_list_objects_accepts_windows_style_prefix_as_opaque_on_posix(tmp_path: Path) -> None:
    page = build_storage(tmp_path).list_objects(StorageLocation.USER_MEDIA, prefix="C:\\absolute", limit=10)

    assert page.objects == ()


def test_local_list_objects_is_recursive_sorted_and_paginated(tmp_path: Path) -> None:
    root = tmp_path / "uploads"
    files = {
        "imports/source/owner-2/job-2/c.jpg": b"ccc",
        "imports/source/owner-1/job-1/a.jpg": b"a",
        "imports/source/owner-1/job-1/b.jpg": b"bb",
        "recipes/media/owner-1/recipe-1/d.jpg": b"dddd",
    }
    for key, content in files.items():
        path = root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    storage = build_storage(tmp_path)
    first = storage.list_objects(StorageLocation.USER_MEDIA, prefix="imports/source/", limit=2)
    second = storage.list_objects(
        StorageLocation.USER_MEDIA,
        prefix="imports/source/",
        limit=2,
        cursor=first.next_cursor,
    )

    assert [item.storage_key for item in first.objects] == [
        "imports/source/owner-1/job-1/a.jpg",
        "imports/source/owner-1/job-1/b.jpg",
    ]
    assert [item.size_bytes for item in first.objects] == [1, 2]
    assert all(item.last_modified_at.tzinfo is timezone.utc for item in first.objects)
    assert first.next_cursor == "imports/source/owner-1/job-1/b.jpg"
    assert [item.storage_key for item in second.objects] == ["imports/source/owner-2/job-2/c.jpg"]
    assert second.next_cursor is None
