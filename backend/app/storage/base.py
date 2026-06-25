from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    original_name: str
    mime_type: str
    size_bytes: int


class StorageService(Protocol):
    def save(self, content: bytes, original_name: str, mime_type: str) -> StoredFile:
        raise NotImplementedError

    def read(self, storage_key: str) -> bytes:
        raise NotImplementedError

    def delete(self, storage_key: str) -> None:
        raise NotImplementedError
