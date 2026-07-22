from dataclasses import dataclass
from pathlib import Path

from app.storage.constants import StoragePurpose

StorageLocator = Path | str


@dataclass(frozen=True)
class StorageWriteContext:
    owner_id: str
    purpose: StoragePurpose
    entity_id: str


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    original_name: str
    mime_type: str
    size_bytes: int
