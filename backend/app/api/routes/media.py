from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.deps import CurrentUserDep, SessionDep
from app.media.access.constants import MediaReferenceType
from app.media.access.runtime import get_download_access_provider
from app.media.access.service import MediaAccessService
from app.schemas.media import MediaAccessRequest, MediaAccessResponse, MediaReferenceIn

router = APIRouter(prefix="/media", tags=["media"])


@router.post("/access", response_model=MediaAccessResponse)
def create_media_access(
    request: MediaAccessRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> MediaAccessResponse:
    service = MediaAccessService(session, get_download_access_provider())
    return MediaAccessResponse(items=service.create_grants(current_user.id, request.items))


@router.get("/{media_type}/{media_id}", response_class=FileResponse)
def get_media(
    media_type: MediaReferenceType,
    media_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> FileResponse:
    service = MediaAccessService(session, get_download_access_provider())
    path, content_type = service.get_local_media(
        current_user.id,
        MediaReferenceIn(type=media_type, id=media_id),
    )
    return FileResponse(Path(path), media_type=content_type)
