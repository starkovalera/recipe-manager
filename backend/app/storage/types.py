from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.storage.constants import StorageSystemPurpose, StorageUserPurpose
from app.storage.keys import build_system_storage_key, build_user_storage_key, build_user_storage_prefix

StorageLocator = Path | str


@runtime_checkable
class StorageSaveContext(Protocol):
    def build_storage_key(self, *, original_name: str, mime_type: str) -> str: ...


@dataclass(frozen=True)
class StorageUserContext:
    owner_id: str
    purpose: StorageUserPurpose
    entity_id: str

    def build_prefix(self) -> str:
        return build_user_storage_prefix(owner_id=self.owner_id, purpose=self.purpose, entity_id=self.entity_id)

    def build_storage_key(self, *, original_name: str, mime_type: str) -> str:
        return build_user_storage_key(
            owner_id=self.owner_id,
            purpose=self.purpose,
            entity_id=self.entity_id,
            mime_type=mime_type,
        )


@dataclass(frozen=True)
class StorageSystemContext:
    purpose: StorageSystemPurpose
    report_type: str
    report_id: str
    created_at: datetime

    def build_storage_key(self, *, original_name: str, mime_type: str) -> str:
        return build_system_storage_key(
            purpose=self.purpose,
            report_type=self.report_type,
            report_id=self.report_id,
            created_at=self.created_at,
            mime_type=mime_type,
        )


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    original_name: str
    mime_type: str
    size_bytes: int


@dataclass(frozen=True)
class StorageObjectInfo:
    storage_key: str
    size_bytes: int
    last_modified_at: datetime


@dataclass(frozen=True)
class StorageObjectPage:
    objects: tuple[StorageObjectInfo, ...]
    next_cursor: str | None
