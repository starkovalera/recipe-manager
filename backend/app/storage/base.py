from typing import Protocol

from app.storage.constants import StorageLocation
from app.storage.types import StorageWriteContext, StoredFile


class StorageService(Protocol):
    def save(
        self,
        location: StorageLocation,
        content: bytes,
        original_name: str,
        mime_type: str,
        *,
        context: StorageWriteContext,
    ) -> StoredFile:
        raise NotImplementedError

    def read(self, location: StorageLocation, storage_key: str) -> bytes:
        raise NotImplementedError

    def delete(self, location: StorageLocation, storage_key: str) -> None:
        raise NotImplementedError
