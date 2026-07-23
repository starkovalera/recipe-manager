from app.storage.base import StorageService
from app.storage.constants import StorageLocation
from app.storage.types import StorageObjectInfo


def list_all_storage_objects(
    storage: StorageService,
    location: StorageLocation,
    *,
    prefix: str,
) -> list[StorageObjectInfo]:
    objects: list[StorageObjectInfo] = []
    cursor: str | None = None
    while True:
        page = storage.list_objects(location, prefix=prefix, limit=1000, cursor=cursor)
        objects.extend(page.objects)
        if page.next_cursor is None:
            return objects
        cursor = page.next_cursor
