from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.errors import StorageNotFoundError
from app.storage.local import LocalStorageService

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{storage_key:path}")
def get_media(storage_key: str) -> FileResponse:
    storage = LocalStorageService(get_settings().upload_dir)
    try:
        path = storage.path_for_response(storage_key)
    except ValueError as error:
        raise StorageNotFoundError() from error
    if not path.exists() or not path.is_file():
        raise StorageNotFoundError()
    return FileResponse(path)
