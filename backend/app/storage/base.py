from typing import Protocol

from app.storage.constants import StorageLocation
from app.storage.types import StorageObjectPage, StorageSaveContext, StoredFile


class StorageService(Protocol):
    def is_safe_key(self, location: StorageLocation, storage_key: str) -> bool:
        raise NotImplementedError

    def save(
        self,
        location: StorageLocation,
        content: bytes,
        original_name: str,
        mime_type: str,
        *,
        context: StorageSaveContext,
    ) -> StoredFile:
        raise NotImplementedError

    def read(self, location: StorageLocation, storage_key: str) -> bytes:
        raise NotImplementedError

    def delete(self, location: StorageLocation, storage_key: str) -> None:
        raise NotImplementedError

    def list_objects(
        self,
        location: StorageLocation,
        *,
        prefix: str,
        limit: int,
        cursor: str | None = None,
    ) -> StorageObjectPage:
        raise NotImplementedError
