from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.errors import MediaAccessNotAvailableError, StorageNotFoundError
from app.storage.constants import StorageLocation
from app.storage.local import LocalStorageService
from app.storage.runtime import get_storage_service

router = APIRouter(tags=["media"])


def _get_local_media(storage_key: str) -> FileResponse:
    storage = get_storage_service()
    if not isinstance(storage, LocalStorageService):
        raise MediaAccessNotAvailableError()
    try:
        path = storage.path_for_response(StorageLocation.USER_MEDIA, storage_key)
    except ValueError as error:
        raise StorageNotFoundError() from error
    if not path.exists() or not path.is_file():
        raise StorageNotFoundError()
    return FileResponse(path)


@router.get("/media/{namespace}/{kind}/{owner_id}/{entity_id}/{object_name}")
def get_media(namespace: str, kind: str, owner_id: str, entity_id: str, object_name: str) -> FileResponse:
    return _get_local_media("/".join((namespace, kind, owner_id, entity_id, object_name)))
