import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.storage.constants import StorageLocation, StorageUserPurpose
from app.storage.errors import StorageConfigurationError, StorageObjectNotFoundError
from app.storage.local import LocalStorageService
from app.storage.types import StorageUserContext


@dataclass(frozen=True)
class FixedContext:
    key: str

    def build_storage_key(self, *, original_name: str, mime_type: str) -> str:
        return self.key


def build_storage(tmp_path: Path) -> LocalStorageService:
    return LocalStorageService(
        location_to_locator={
            StorageLocation.USER_MEDIA: tmp_path / "uploads",
            StorageLocation.SYSTEM_ARTIFACTS: tmp_path / "system-artifacts",
        },
    )


def test_local_storage_requires_configured_path_locator(tmp_path: Path) -> None:
    with pytest.raises(StorageConfigurationError, match="USER_MEDIA"):
        LocalStorageService(location_to_locator={})
    with pytest.raises(StorageConfigurationError, match="Path"):
        LocalStorageService(
            location_to_locator={
                StorageLocation.USER_MEDIA: "bucket-name",
                StorageLocation.SYSTEM_ARTIFACTS: tmp_path / "system-artifacts",
            }
        )


def test_local_storage_saves_reads_and_deletes_nested_key(tmp_path: Path) -> None:
    storage = build_storage(tmp_path)
    context = StorageUserContext(
        owner_id="owner-1",
        purpose=StorageUserPurpose.IMPORT_SOURCE,
        entity_id="job-1",
    )

    saved = storage.save(
        StorageLocation.USER_MEDIA,
        b"hello",
        original_name="hello.jpg",
        mime_type="image/jpeg",
        context=context,
    )

    assert saved.storage_key.startswith("imports/source/owner-1/job-1/")
    assert saved.storage_key.endswith(".jpg")
    assert saved.original_name == "hello.jpg"
    assert saved.mime_type == "image/jpeg"
    assert saved.size_bytes == 5
    assert storage.read(StorageLocation.USER_MEDIA, saved.storage_key) == b"hello"
    storage.delete(StorageLocation.USER_MEDIA, saved.storage_key)
    storage.delete(StorageLocation.USER_MEDIA, saved.storage_key)
    with pytest.raises(StorageObjectNotFoundError):
        storage.read(StorageLocation.USER_MEDIA, saved.storage_key)


def test_local_storage_uses_context_generated_key(tmp_path: Path) -> None:
    storage = build_storage(tmp_path)

    saved = storage.save(
        StorageLocation.USER_MEDIA,
        b"report",
        "ignored.json",
        "application/json",
        context=FixedContext("custom/report.json"),
    )

    assert saved.storage_key == "custom/report.json"
    assert storage.read(StorageLocation.USER_MEDIA, saved.storage_key) == b"report"


@pytest.mark.parametrize(
    "storage_key",
    ["../outside", "nested/../../outside", "/absolute"],
)
def test_local_storage_rejects_keys_outside_location(tmp_path: Path, storage_key: str) -> None:
    storage = build_storage(tmp_path)

    with pytest.raises(ValueError, match="outside storage root"):
        storage.read(StorageLocation.USER_MEDIA, storage_key)


@pytest.mark.skipif(os.name != "nt", reason="Windows path semantics are runtime-specific.")
@pytest.mark.parametrize("storage_key", ["..\\outside", "C:\\absolute"])
def test_local_storage_rejects_windows_paths_outside_location(tmp_path: Path, storage_key: str) -> None:
    storage = build_storage(tmp_path)

    with pytest.raises(ValueError, match="outside storage root"):
        storage.read(StorageLocation.USER_MEDIA, storage_key)


def test_local_storage_exposes_local_path_for_response(tmp_path: Path) -> None:
    storage = build_storage(tmp_path)
    storage_key = "recipes/media/owner-1/recipe-1/image.jpg"

    assert storage.path_for_response(StorageLocation.USER_MEDIA, storage_key) == (tmp_path / "uploads" / storage_key).resolve()


def test_local_storage_key_safety_uses_runtime_path_rules(tmp_path: Path) -> None:
    storage = build_storage(tmp_path)

    assert storage.is_safe_key(StorageLocation.USER_MEDIA, "imports/source/job/image.jpg") is True
    assert storage.is_safe_key(StorageLocation.USER_MEDIA, "../outside.jpg") is False
    assert storage.is_safe_key(StorageLocation.USER_MEDIA, "/absolute.jpg") is False
    assert storage.is_safe_key(StorageLocation.USER_MEDIA, "..\\outside.jpg") is (os.name != "nt")
