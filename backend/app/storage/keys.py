import re
import uuid
from collections.abc import Mapping

from app.storage.constants import StoragePurpose
from app.storage.types import StorageWriteContext

# Stable object-key roots used by storage lifecycle and IAM policies.
STORAGE_PURPOSE_PREFIXES: Mapping[StoragePurpose, str] = {
    StoragePurpose.IMPORT_SOURCE: "imports/source",
    StoragePurpose.IMPORT_DERIVED: "imports/derived",
    StoragePurpose.RECIPE_MEDIA: "recipes/media",
    StoragePurpose.TEMPORARY: "temporary",
}

# Explicit MIME allowlist prevents caller-controlled filename extensions.
MIME_TYPE_EXTENSIONS: Mapping[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/ogg": ".ogg",
}

_STORAGE_KEY_SEGMENT = re.compile(r"[A-Za-z0-9_-]+")


def _validate_storage_key_segment(value: str) -> str:
    if not _STORAGE_KEY_SEGMENT.fullmatch(value):
        raise ValueError("Invalid storage key segment.")
    return value


def build_storage_key(
    context: StorageWriteContext,
    *,
    mime_type: str,
) -> str:
    owner_id = _validate_storage_key_segment(context.owner_id)
    entity_id = _validate_storage_key_segment(context.entity_id)
    extension = MIME_TYPE_EXTENSIONS.get(mime_type.strip().lower(), "")
    object_name = f"{uuid.uuid4().hex}{extension}"
    return f"{STORAGE_PURPOSE_PREFIXES[context.purpose]}/{owner_id}/{entity_id}/{object_name}"
