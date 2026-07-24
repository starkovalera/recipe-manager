from collections.abc import Callable, Sequence
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.errors import MediaNotFoundError
from app.media.access.constants import MediaItemErrorCode, MediaReferenceType
from app.media.access.queries import resolve_import_source_images, resolve_recipe_images
from app.media.access.types import (
    AuthorizedMedia,
    DownloadAccessProvider,
    DownloadGrant,
    MediaReference,
    MediaReferenceUnavailableError,
)
from app.schemas.media import DownloadGrantOut, MediaAccessItemErrorOut, MediaAccessItemOut, MediaReferenceIn

Resolver = Callable[..., dict[str, AuthorizedMedia]]

MEDIA_RESOLVERS: dict[MediaReferenceType, Resolver] = {
    MediaReferenceType.RECIPE_IMAGE: resolve_recipe_images,
    MediaReferenceType.IMPORT_SOURCE_IMAGE: resolve_import_source_images,
}


class MediaAccessService:
    def __init__(self, session: Session, provider: DownloadAccessProvider) -> None:
        self._session = session
        self._provider = provider

    def _resolve(self, owner_id: str, references: Sequence[MediaReferenceIn]) -> dict[MediaReference, AuthorizedMedia]:
        resolved: dict[MediaReference, AuthorizedMedia] = {}
        for reference_type, resolver in MEDIA_RESOLVERS.items():
            ids = {reference.id for reference in references if reference.type is reference_type}
            resolved_media = resolver(self._session, owner_id=owner_id, media_ids=ids)
            for media_id, media in resolved_media.items():
                resolved[MediaReference(reference_type, media_id)] = media
        return resolved

    def create_grants(self, owner_id: str, references: Sequence[MediaReferenceIn]) -> list[MediaAccessItemOut]:
        resolved = self._resolve(owner_id, references)
        grants: dict[MediaReference, DownloadGrant] = {}
        for reference, media in resolved.items():
            try:
                grants[reference] = self._provider.create_grant(media)
            except MediaReferenceUnavailableError:
                continue
        results: list[MediaAccessItemOut] = []
        for item in references:
            reference = MediaReference(item.type, item.id)
            grant = grants.get(reference)
            if grant is None:
                results.append(
                    MediaAccessItemOut(
                        type=item.type,
                        id=item.id,
                        error=MediaAccessItemErrorOut(
                            code=MediaItemErrorCode.MEDIA_NOT_FOUND,
                            message="Media is unavailable.",
                        ),
                    )
                )
            else:
                results.append(MediaAccessItemOut(type=item.type, id=item.id, grant=DownloadGrantOut.model_validate(grant)))
        return results

    def get_local_media(self, owner_id: str, reference: MediaReferenceIn) -> tuple[Path, str]:
        resolved = self._resolve(owner_id, [reference]).get(MediaReference(reference.type, reference.id))
        if resolved is None:
            raise MediaNotFoundError()
        try:
            return self._provider.get_local_path(resolved), resolved.content_type
        except MediaReferenceUnavailableError as error:
            raise MediaNotFoundError() from error
