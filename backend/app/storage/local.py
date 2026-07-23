from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

from app.storage.base import StorageService
from app.storage.constants import StorageLocation
from app.storage.errors import StorageConfigurationError, StorageObjectNotFoundError, StorageOperationError
from app.storage.types import StorageLocator, StorageObjectInfo, StorageObjectPage, StorageSaveContext, StoredFile


class LocalStorageService(StorageService):
    def __init__(
        self,
        *,
        location_to_locator: Mapping[StorageLocation, StorageLocator],
    ) -> None:
        roots: dict[StorageLocation, Path] = {}
        for location in StorageLocation:
            locator = location_to_locator.get(location)
            if locator is None:
                raise StorageConfigurationError(f"Storage location {location.value} is not configured.")
            if not isinstance(locator, Path):
                raise StorageConfigurationError(f"LOCAL storage location {location.value} requires a Path locator.")
            root = locator.resolve()
            root.mkdir(parents=True, exist_ok=True)
            roots[location] = root
        self._roots = roots

    def _path_for(self, location: StorageLocation, storage_key: str) -> Path:
        root = self._roots.get(location)
        if root is None:
            raise StorageConfigurationError(f"Storage location {location.value} is not configured.")
        posix_key = PurePosixPath(storage_key)
        windows_key = PureWindowsPath(storage_key)
        if posix_key.is_absolute() or windows_key.is_absolute() or ".." in posix_key.parts or ".." in windows_key.parts:
            raise ValueError(f"Storage key resolves outside storage root: {storage_key}")
        path = (root / storage_key).resolve()
        if root != path and root not in path.parents:
            raise ValueError(f"Storage key resolves outside storage root: {storage_key}")
        return path

    def save(
        self,
        location: StorageLocation,
        content: bytes,
        original_name: str,
        mime_type: str,
        *,
        context: StorageSaveContext,
    ) -> StoredFile:
        storage_key = context.build_storage_key(original_name=original_name, mime_type=mime_type)
        path = self._path_for(location, storage_key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        except OSError as error:
            raise StorageOperationError("Local storage write failed.") from error
        return StoredFile(
            storage_key=storage_key,
            original_name=original_name,
            mime_type=mime_type,
            size_bytes=len(content),
        )

    def read(self, location: StorageLocation, storage_key: str) -> bytes:
        path = self._path_for(location, storage_key)
        try:
            return path.read_bytes()
        except FileNotFoundError as error:
            raise StorageObjectNotFoundError("Storage object was not found.") from error
        except OSError as error:
            raise StorageOperationError("Local storage read failed.") from error

    def delete(self, location: StorageLocation, storage_key: str) -> None:
        path = self._path_for(location, storage_key)
        try:
            path.unlink(missing_ok=True)
        except OSError as error:
            raise StorageOperationError("Local storage delete failed.") from error

    def path_for_response(self, location: StorageLocation, storage_key: str) -> Path:
        return self._path_for(location, storage_key)

    def list_objects(
        self,
        location: StorageLocation,
        *,
        prefix: str,
        limit: int,
        cursor: str | None = None,
    ) -> StorageObjectPage:
        if not 1 <= limit <= 1000:
            raise ValueError("Storage listing limit must be between 1 and 1000.")
        posix_prefix = PurePosixPath(prefix or ".")
        windows_prefix = PureWindowsPath(prefix or ".")
        if posix_prefix.is_absolute() or windows_prefix.is_absolute() or ".." in posix_prefix.parts or ".." in windows_prefix.parts:
            raise ValueError("Storage listing prefix must be a safe relative prefix.")
        if cursor is not None:
            self._path_for(location, cursor)

        root = self._roots[location]
        try:
            keys = sorted(
                path.relative_to(root).as_posix()
                for path in root.rglob("*")
                if path.is_file()
                and path.relative_to(root).as_posix().startswith(prefix)
                and (cursor is None or path.relative_to(root).as_posix() > cursor)
            )
            selected_keys = keys[: limit + 1]
            has_more = len(selected_keys) > limit
            selected_keys = selected_keys[:limit]
            objects = tuple(
                StorageObjectInfo(
                    storage_key=key,
                    size_bytes=(root / key).stat().st_size,
                    last_modified_at=datetime.fromtimestamp((root / key).stat().st_mtime, timezone.utc),
                )
                for key in selected_keys
            )
        except OSError as error:
            raise StorageOperationError("Local storage listing failed.") from error

        return StorageObjectPage(
            objects=objects,
            next_cursor=selected_keys[-1] if has_more else None,
        )
