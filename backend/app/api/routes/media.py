from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.errors import StorageNotFoundError
from app.storage.runtime import get_storage_service

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{storage_key:path}")
def get_media(storage_key: str) -> FileResponse:
    storage = get_storage_service()
    try:
        path = storage.path_for_response(storage_key)
    except ValueError as error:
        raise StorageNotFoundError() from error
    if not path.exists() or not path.is_file():
        raise StorageNotFoundError()
    return FileResponse(path)
