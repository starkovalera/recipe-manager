import inspect
from dataclasses import FrozenInstanceError

import pytest

from app.storage.base import StorageService
from app.storage.constants import StorageLocation, StoragePurpose
from app.storage.types import StorageWriteContext


def test_storage_enums_have_exact_p9_values() -> None:
    assert list(StorageLocation) == [StorageLocation.USER_MEDIA]
    assert StorageLocation.USER_MEDIA.value == "USER_MEDIA"
    assert list(StoragePurpose) == [
        StoragePurpose.IMPORT_SOURCE,
        StoragePurpose.IMPORT_DERIVED,
        StoragePurpose.RECIPE_MEDIA,
        StoragePurpose.TEMPORARY,
    ]
    assert [purpose.value for purpose in StoragePurpose] == [
        "IMPORT_SOURCE",
        "IMPORT_DERIVED",
        "RECIPE_MEDIA",
        "TEMPORARY",
    ]


def test_storage_write_context_is_immutable() -> None:
    context = StorageWriteContext(
        owner_id="owner-1",
        purpose=StoragePurpose.IMPORT_SOURCE,
        entity_id="job-1",
    )

    with pytest.raises(FrozenInstanceError):
        context.owner_id = "owner-2"  # type: ignore[misc]


def test_storage_service_requires_location_and_write_context() -> None:
    save = inspect.signature(StorageService.save)
    read = inspect.signature(StorageService.read)
    delete = inspect.signature(StorageService.delete)

    assert list(save.parameters) == ["self", "location", "content", "original_name", "mime_type", "context"]
    assert save.parameters["context"].kind is inspect.Parameter.KEYWORD_ONLY
    assert list(read.parameters) == ["self", "location", "storage_key"]
    assert list(delete.parameters) == ["self", "location", "storage_key"]
    assert not hasattr(StorageService, "path_for_response")
