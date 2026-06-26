from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.storage.local import LocalStorageService


router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{storage_key:path}")
def get_media(storage_key: str) -> FileResponse:
    storage = LocalStorageService(get_settings().upload_dir)
    try:
        path = storage.path_for_response(storage_key)
    except ValueError as error:
        raise ApiError(ErrorCode.STORAGE_NOT_FOUND, "Media file not found.", status_code=404) from error
    if not path.exists() or not path.is_file():
        raise ApiError(ErrorCode.STORAGE_NOT_FOUND, "Media file not found.", status_code=404)
    return FileResponse(path)
