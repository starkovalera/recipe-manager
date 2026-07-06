import uuid
from pathlib import Path

from app.storage.base import StorageService, StoredFile


class LocalStorageService(StorageService):
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, storage_key: str) -> Path:
        path = (self.root / storage_key).resolve()
        if self.root != path and self.root not in path.parents:
            raise ValueError(f"Storage key resolves outside storage root: {storage_key}")
        return path

    def save(self, content: bytes, original_name: str, mime_type: str) -> StoredFile:
        suffix = Path(original_name).suffix.lower()
        storage_key = f"{uuid.uuid4().hex}{suffix}"
        path = self._path_for(storage_key)
        path.write_bytes(content)
        return StoredFile(
            storage_key=storage_key,
            original_name=original_name,
            mime_type=mime_type,
            size_bytes=len(content),
        )

    def read(self, storage_key: str) -> bytes:
        return self._path_for(storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        path = self._path_for(storage_key)
        if path.exists():
            path.unlink()

    def path_for_response(self, storage_key: str) -> Path:
        return self._path_for(storage_key)
