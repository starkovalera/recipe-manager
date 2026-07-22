from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.errors import MediaAccessNotAvailableError, StorageNotFoundError
from app.storage.constants import StorageLocation
from app.storage.local import LocalStorageService
from app.storage.runtime import get_storage_service

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{storage_key:path}")
def get_media(storage_key: str) -> FileResponse:
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
