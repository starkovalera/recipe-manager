import re
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone

from app.storage.constants import StorageSystemPurpose, StorageUserPurpose

# Stable object-key roots used by storage lifecycle and IAM policies.
STORAGE_USER_PURPOSE_PREFIXES: Mapping[StorageUserPurpose, str] = {
    StorageUserPurpose.IMPORT_SOURCE: "imports/source",
    StorageUserPurpose.IMPORT_DERIVED: "imports/derived",
    StorageUserPurpose.RECIPE_MEDIA: "recipes/media",
}

STORAGE_SYSTEM_PURPOSE_PREFIXES: Mapping[StorageSystemPurpose, str] = {
    StorageSystemPurpose.MAINTENANCE_REPORT: "maintenance/reports",
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
    "application/json": ".json",
}

_STORAGE_KEY_SEGMENT = re.compile(r"[A-Za-z0-9_-]+")


def _validate_storage_key_segment(value: str) -> str:
    if not _STORAGE_KEY_SEGMENT.fullmatch(value):
        raise ValueError("Invalid storage key segment.")
    return value


def build_user_storage_prefix(
    *,
    owner_id: str,
    purpose: StorageUserPurpose,
    entity_id: str,
) -> str:
    owner_id = _validate_storage_key_segment(owner_id)
    entity_id = _validate_storage_key_segment(entity_id)
    return f"{STORAGE_USER_PURPOSE_PREFIXES[purpose]}/{owner_id}/{entity_id}"


def build_user_storage_key(
    *,
    owner_id: str,
    purpose: StorageUserPurpose,
    entity_id: str,
    mime_type: str,
) -> str:
    extension = MIME_TYPE_EXTENSIONS.get(mime_type.strip().lower(), "")
    object_name = f"{uuid.uuid4().hex}{extension}"
    prefix = build_user_storage_prefix(owner_id=owner_id, purpose=purpose, entity_id=entity_id)
    return f"{prefix}/{object_name}"


def build_system_storage_key(
    *,
    purpose: StorageSystemPurpose,
    report_type: str,
    report_id: str,
    created_at: datetime,
    mime_type: str,
) -> str:
    report_type = _validate_storage_key_segment(report_type)
    report_id = _validate_storage_key_segment(report_id)
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("System storage timestamps must be timezone-aware.")
    if mime_type.strip().lower() != "application/json":
        raise ValueError("Maintenance reports require application/json MIME type.")
    created_at = created_at.astimezone(timezone.utc)
    date_path = created_at.strftime("%Y/%m/%d")
    object_name = f"{created_at.strftime('%Y%m%dT%H%M%SZ')}-{report_id}.json"
    return f"{STORAGE_SYSTEM_PURPOSE_PREFIXES[purpose]}/{report_type}/{date_path}/{object_name}"
