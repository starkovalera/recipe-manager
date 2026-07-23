import inspect
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from app.storage.base import StorageService
from app.storage.constants import StorageLocation, StorageSystemPurpose, StorageUserPurpose
from app.storage.types import StorageSaveContext, StorageSystemContext, StorageUserContext


def test_storage_enums_have_exact_iteration_9_values() -> None:
    assert list(StorageLocation) == [StorageLocation.USER_MEDIA, StorageLocation.SYSTEM_ARTIFACTS]
    assert list(StorageUserPurpose) == [
        StorageUserPurpose.IMPORT_SOURCE,
        StorageUserPurpose.IMPORT_DERIVED,
        StorageUserPurpose.RECIPE_MEDIA,
    ]
    assert list(StorageSystemPurpose) == [StorageSystemPurpose.MAINTENANCE_REPORT]
    assert not hasattr(StorageUserPurpose, "TEMPORARY")


def test_storage_contexts_are_immutable_and_implement_save_context() -> None:
    user_context = StorageUserContext(
        owner_id="owner-1",
        purpose=StorageUserPurpose.IMPORT_SOURCE,
        entity_id="job-1",
    )
    system_context = StorageSystemContext(
        purpose=StorageSystemPurpose.MAINTENANCE_REPORT,
        report_type="integrity-check",
        report_id="report-1",
        created_at=datetime(2026, 7, 23, 10, 0, tzinfo=timezone.utc),
    )

    assert isinstance(user_context, StorageSaveContext)
    assert isinstance(system_context, StorageSaveContext)
    with pytest.raises(FrozenInstanceError):
        user_context.owner_id = "owner-2"  # type: ignore[misc]


def test_storage_service_requires_location_and_save_context() -> None:
    save = inspect.signature(StorageService.save)
    read = inspect.signature(StorageService.read)
    delete = inspect.signature(StorageService.delete)
    is_safe_key = inspect.signature(StorageService.is_safe_key)
    list_all_objects = inspect.signature(StorageService.list_all_objects)

    assert list(save.parameters) == ["self", "location", "content", "original_name", "mime_type", "context"]
    assert save.parameters["context"].kind is inspect.Parameter.KEYWORD_ONLY
    assert save.parameters["context"].annotation is StorageSaveContext
    assert list(read.parameters) == ["self", "location", "storage_key"]
    assert list(delete.parameters) == ["self", "location", "storage_key"]
    assert list(is_safe_key.parameters) == ["self", "location", "storage_key"]
    assert list(list_all_objects.parameters) == ["self", "location", "prefix"]
    assert not hasattr(StorageService, "path_for_response")
