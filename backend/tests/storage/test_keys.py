import re

import pytest

from app.storage.constants import StoragePurpose
from app.storage.keys import MIME_TYPE_EXTENSIONS, STORAGE_PURPOSE_PREFIXES, build_storage_key
from app.storage.types import StorageWriteContext


@pytest.mark.parametrize(
    ("purpose", "prefix"),
    [
        (StoragePurpose.IMPORT_SOURCE, "imports/source"),
        (StoragePurpose.IMPORT_DERIVED, "imports/derived"),
        (StoragePurpose.RECIPE_MEDIA, "recipes/media"),
        (StoragePurpose.TEMPORARY, "temporary"),
    ],
)
def test_build_storage_key_uses_exact_purpose_first_prefix(purpose: StoragePurpose, prefix: str) -> None:
    context = StorageWriteContext(owner_id="owner-1", purpose=purpose, entity_id="entity-1")

    key = build_storage_key(context, mime_type="image/jpeg")

    assert key.startswith(f"{prefix}/owner-1/entity-1/")
    assert not key.startswith("users/")
    assert re.fullmatch(rf"{re.escape(prefix)}/owner-1/entity-1/[0-9a-f]{{32}}\.jpg", key)


@pytest.mark.parametrize("invalid_segment", ["", "/", "\\", ".", "..", "a/b", "a\\b", "space here", "colon:"])
def test_build_storage_key_rejects_invalid_owner_or_entity_segments(invalid_segment: str) -> None:
    valid = StorageWriteContext(
        owner_id="user_123-abc",
        purpose=StoragePurpose.IMPORT_SOURCE,
        entity_id="job_456-def",
    )

    with pytest.raises(ValueError, match="storage key segment"):
        build_storage_key(
            StorageWriteContext(
                owner_id=invalid_segment,
                purpose=valid.purpose,
                entity_id=valid.entity_id,
            ),
            mime_type="image/png",
        )
    with pytest.raises(ValueError, match="storage key segment"):
        build_storage_key(
            StorageWriteContext(
                owner_id=valid.owner_id,
                purpose=valid.purpose,
                entity_id=invalid_segment,
            ),
            mime_type="image/png",
        )


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
def test_build_storage_key_uses_allowlisted_mime_extension(mime_type: str, extension: str) -> None:
    context = StorageWriteContext(
        owner_id="owner-1",
        purpose=StoragePurpose.IMPORT_DERIVED,
        entity_id="job-1",
    )

    key = build_storage_key(context, mime_type=mime_type)

    assert key.endswith(extension)
    assert "original filename" not in key


def test_build_storage_key_has_deterministic_prefix_and_unique_object_name() -> None:
    context = StorageWriteContext(
        owner_id="owner-1",
        purpose=StoragePurpose.RECIPE_MEDIA,
        entity_id="recipe-1",
    )

    first = build_storage_key(context, mime_type="image/jpeg")
    second = build_storage_key(context, mime_type="image/jpeg")

    assert first.rsplit("/", 1)[0] == second.rsplit("/", 1)[0]
    assert first != second
    assert STORAGE_PURPOSE_PREFIXES[StoragePurpose.RECIPE_MEDIA] == "recipes/media"
    assert MIME_TYPE_EXTENSIONS["image/jpeg"] == ".jpg"
