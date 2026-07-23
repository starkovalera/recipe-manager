import re
from datetime import datetime, timezone

import pytest

from app.storage.constants import StorageSystemPurpose, StorageUserPurpose
from app.storage.keys import MIME_TYPE_EXTENSIONS, STORAGE_USER_PURPOSE_PREFIXES
from app.storage.types import StorageSystemContext, StorageUserContext


@pytest.mark.parametrize(
    ("purpose", "prefix"),
    [
        (StorageUserPurpose.IMPORT_SOURCE, "imports/source"),
        (StorageUserPurpose.IMPORT_DERIVED, "imports/derived"),
        (StorageUserPurpose.RECIPE_MEDIA, "recipes/media"),
    ],
)
def test_user_context_builds_purpose_first_key(purpose: StorageUserPurpose, prefix: str) -> None:
    context = StorageUserContext(owner_id="owner-1", purpose=purpose, entity_id="entity-1")

    assert context.build_prefix() == f"{prefix}/owner-1/entity-1"
    key = context.build_storage_key(original_name="ignored.png", mime_type="image/jpeg")

    assert re.fullmatch(rf"{re.escape(prefix)}/owner-1/entity-1/[0-9a-f]{{32}}\.jpg", key)
    assert not key.startswith("users/")


@pytest.mark.parametrize("invalid_segment", ["", "/", "\\", ".", "..", "a/b", "a\\b", "space here", "colon:"])
def test_user_context_rejects_invalid_owner_or_entity_segments(invalid_segment: str) -> None:
    valid = StorageUserContext(
        owner_id="user_123-abc",
        purpose=StorageUserPurpose.IMPORT_SOURCE,
        entity_id="job_456-def",
    )

    with pytest.raises(ValueError, match="storage key segment"):
        StorageUserContext(invalid_segment, valid.purpose, valid.entity_id).build_prefix()
    with pytest.raises(ValueError, match="storage key segment"):
        StorageUserContext(valid.owner_id, valid.purpose, invalid_segment).build_prefix()


@pytest.mark.parametrize(
    ("mime_type", "extension"),
    [
        ("image/jpeg", ".jpg"),
        ("image/png", ".png"),
        ("image/webp", ".webp"),
        ("video/mp4", ".mp4"),
        ("audio/mpeg", ".mp3"),
        ("audio/mp4", ".m4a"),
        ("audio/wav", ".wav"),
        ("audio/ogg", ".ogg"),
        ("application/octet-stream", ""),
    ],
)
def test_user_context_uses_allowlisted_mime_extension(mime_type: str, extension: str) -> None:
    context = StorageUserContext("owner-1", StorageUserPurpose.IMPORT_DERIVED, "job-1")

    key = context.build_storage_key(original_name="original filename.txt", mime_type=mime_type)

    assert key.endswith(extension)
    assert "original filename" not in key


def test_system_context_builds_deterministic_report_key() -> None:
    context = StorageSystemContext(
        purpose=StorageSystemPurpose.MAINTENANCE_REPORT,
        report_type="orphaned-upload-detection",
        report_id="report_1",
        created_at=datetime(2026, 7, 23, 10, 0, tzinfo=timezone.utc),
    )

    assert context.build_storage_key(original_name="report.json", mime_type="application/json") == (
        "maintenance/reports/orphaned-upload-detection/2026/07/23/20260723T100000Z-report_1.json"
    )


@pytest.mark.parametrize("invalid_segment", ["", "../report", "report/type", "space here"])
def test_system_context_rejects_invalid_segments(invalid_segment: str) -> None:
    context = StorageSystemContext(
        purpose=StorageSystemPurpose.MAINTENANCE_REPORT,
        report_type=invalid_segment,
        report_id="report-1",
        created_at=datetime.now(timezone.utc),
    )

    with pytest.raises(ValueError, match="storage key segment"):
        context.build_storage_key(original_name="report.json", mime_type="application/json")


def test_system_context_rejects_naive_timestamp_and_non_json_mime() -> None:
    naive = StorageSystemContext(
        purpose=StorageSystemPurpose.MAINTENANCE_REPORT,
        report_type="integrity-check",
        report_id="report-1",
        created_at=datetime(2026, 7, 23, 10, 0),
    )
    aware = StorageSystemContext(
        purpose=StorageSystemPurpose.MAINTENANCE_REPORT,
        report_type="integrity-check",
        report_id="report-1",
        created_at=datetime(2026, 7, 23, 10, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        naive.build_storage_key(original_name="report.json", mime_type="application/json")
    with pytest.raises(ValueError, match="application/json"):
        aware.build_storage_key(original_name="report.txt", mime_type="text/plain")


def test_user_keys_keep_stable_prefix_map() -> None:
    assert STORAGE_USER_PURPOSE_PREFIXES[StorageUserPurpose.RECIPE_MEDIA] == "recipes/media"
    assert MIME_TYPE_EXTENSIONS["image/jpeg"] == ".jpg"
