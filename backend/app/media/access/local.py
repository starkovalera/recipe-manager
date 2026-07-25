from pathlib import Path

from app.media.access.constants import DownloadAccessMode
from app.media.access.types import AuthorizedMedia, DownloadGrant, MediaReferenceUnavailableError
from app.storage.local import LocalStorageService


class LocalDownloadAccessProvider:
    def __init__(self, storage: LocalStorageService) -> None:
        self._storage = storage

    def create_grant(self, media: AuthorizedMedia) -> DownloadGrant:
        if not self._storage.is_safe_key(media.location, media.storage_key):
            raise MediaReferenceUnavailableError()
        return DownloadGrant(
            url=f"/media/{media.reference.type.value}/{media.reference.id}",
            expires_at=None,
            content_type=media.content_type,
            access_mode=DownloadAccessMode.AUTHENTICATED_FETCH,
        )

    def get_local_path(self, media: AuthorizedMedia) -> Path:
        try:
            path = self._storage.path_for_response(media.location, media.storage_key)
        except ValueError as error:
            raise MediaReferenceUnavailableError() from error
        if not path.is_file():
            raise MediaReferenceUnavailableError()
        return path
