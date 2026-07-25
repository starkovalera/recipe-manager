from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.media.access.constants import MediaReferenceType
from app.media.access.types import AuthorizedMedia, MediaReference
from app.models import ImportJob, ImportJobSource, ImportJobStatus, Recipe, RecipeImage, RecipeStatus, SourceType
from app.storage.constants import StorageLocation


def resolve_recipe_images(
    session: Session,
    *,
    owner_id: str,
    media_ids: Collection[str],
) -> dict[str, AuthorizedMedia]:
    if not media_ids:
        return {}
    rows = session.execute(
        select(RecipeImage.id, RecipeImage.storage_key, RecipeImage.mime_type)
        .join(Recipe, Recipe.id == RecipeImage.recipe_id)
        .where(
            RecipeImage.id.in_(media_ids),
            Recipe.owner_id == owner_id,
            Recipe.status == RecipeStatus.ACTIVE,
        )
    )
    return {
        image_id: AuthorizedMedia(
            reference=MediaReference(MediaReferenceType.RECIPE_IMAGE, image_id),
            location=StorageLocation.USER_MEDIA,
            storage_key=storage_key,
            content_type=mime_type,
        )
        for image_id, storage_key, mime_type in rows
        if storage_key and mime_type
    }


def resolve_import_source_images(
    session: Session,
    *,
    owner_id: str,
    media_ids: Collection[str],
) -> dict[str, AuthorizedMedia]:
    if not media_ids:
        return {}
    rows = session.execute(
        select(ImportJobSource.id, ImportJobSource.image_storage_key, ImportJobSource.mime_type)
        .join(ImportJob, ImportJob.id == ImportJobSource.import_job_id)
        .where(
            ImportJobSource.id.in_(media_ids),
            ImportJobSource.type == SourceType.IMAGE,
            ImportJobSource.image_storage_key.is_not(None),
            ImportJob.owner_id == owner_id,
            ImportJob.status != ImportJobStatus.FAILED_ARTIFACTS_REMOVED,
        )
    )
    return {
        source_id: AuthorizedMedia(
            reference=MediaReference(MediaReferenceType.IMPORT_SOURCE_IMAGE, source_id),
            location=StorageLocation.USER_MEDIA,
            storage_key=storage_key,
            content_type=mime_type,
        )
        for source_id, storage_key, mime_type in rows
        if storage_key and mime_type
    }
