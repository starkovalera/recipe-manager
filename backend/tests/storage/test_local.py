from pathlib import Path

import pytest

from app.storage.constants import StorageLocation, StoragePurpose
from app.storage.errors import StorageConfigurationError, StorageObjectNotFoundError
from app.storage.local import LocalStorageService
from app.storage.types import StorageWriteContext


def build_storage(tmp_path: Path) -> LocalStorageService:
    return LocalStorageService(
        location_to_locator={StorageLocation.USER_MEDIA: tmp_path / "uploads"},
    )


def test_local_storage_requires_configured_path_locator(tmp_path: Path) -> None:
    with pytest.raises(StorageConfigurationError, match="USER_MEDIA"):
        LocalStorageService(location_to_locator={})
    with pytest.raises(StorageConfigurationError, match="Path"):
        LocalStorageService(location_to_locator={StorageLocation.USER_MEDIA: "bucket-name"})


def test_local_storage_saves_reads_and_deletes_nested_key(tmp_path: Path) -> None:
    storage = build_storage(tmp_path)
    context = StorageWriteContext(
        owner_id="owner-1",
        purpose=StoragePurpose.IMPORT_SOURCE,
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


def test_local_storage_reads_and_deletes_legacy_flat_key(tmp_path: Path) -> None:
    storage = build_storage(tmp_path)
    legacy_path = tmp_path / "uploads" / "legacy.jpg"
    legacy_path.write_bytes(b"legacy")

    assert storage.read(StorageLocation.USER_MEDIA, "legacy.jpg") == b"legacy"
    storage.delete(StorageLocation.USER_MEDIA, "legacy.jpg")
    assert not legacy_path.exists()


@pytest.mark.parametrize(
    "storage_key",
    ["../outside", "nested/../../outside", "..\\outside", "/absolute", "C:\\absolute"],
)
def test_local_storage_rejects_keys_outside_location(tmp_path: Path, storage_key: str) -> None:
    storage = build_storage(tmp_path)

    with pytest.raises(ValueError, match="outside storage root"):
        storage.read(StorageLocation.USER_MEDIA, storage_key)


def test_local_storage_exposes_local_path_for_response(tmp_path: Path) -> None:
    storage = build_storage(tmp_path)

    assert storage.path_for_response(StorageLocation.USER_MEDIA, "legacy.jpg") == (tmp_path / "uploads" / "legacy.jpg").resolve()
