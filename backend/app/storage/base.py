from abc import ABC, abstractmethod

from app.storage.constants import StorageLocation
from app.storage.types import StorageObjectInfo, StorageObjectPage, StorageSaveContext, StoredFile


class StorageService(ABC):
    @abstractmethod
    def is_safe_key(self, location: StorageLocation, storage_key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
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

    @abstractmethod
    def read(self, location: StorageLocation, storage_key: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def delete(self, location: StorageLocation, storage_key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_objects(
        self,
        location: StorageLocation,
        *,
        prefix: str,
        limit: int,
        cursor: str | None = None,
    ) -> StorageObjectPage:
        raise NotImplementedError

    def list_all_objects(self, location: StorageLocation, *, prefix: str) -> list[StorageObjectInfo]:
        objects: list[StorageObjectInfo] = []
        cursor: str | None = None
        while True:
            page = self.list_objects(location, prefix=prefix, limit=1000, cursor=cursor)
            objects.extend(page.objects)
            if page.next_cursor is None:
                return objects
            cursor = page.next_cursor
