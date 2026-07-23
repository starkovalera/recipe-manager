import logging
from dataclasses import dataclass

import anyio

from app.ai.schemas import ExtractedRecipe
from app.core.config import get_settings
from app.core.logging import bind_logger
from app.imports.constants import IMPORT_LOG_COMPONENT
from app.imports.cover_guard import CoverCandidate as ImportCoverCandidate, CoverGuardInput, choose_cover_candidate
from app.imports.job_context import ImportJobContext
from app.media.images import create_cover_image
from app.models import (
    Recipe,
    RecipeImage,
    RecipeResource,
    RecipeResourceOrigin,
    RecipeResourceRole,
    RecipeResourceStatus,
    SourceType,
)
from app.storage.base import StorageService
from app.storage.constants import StorageLocation, StorageUserPurpose
from app.storage.types import StorageUserContext

logger = logging.getLogger(IMPORT_LOG_COMPONENT)


def _cover_candidate_ref(source_ref: str | None, accepted_refs: set[str]) -> str | None:
    if source_ref is None:
        return None
    if source_ref in accepted_refs:
        return source_ref
    if source_ref.startswith("image:"):
        unprefixed_ref = source_ref.removeprefix("image:")
        if unprefixed_ref in accepted_refs:
            return unprefixed_ref
    image_ref = f"image:{source_ref}"
    return image_ref if image_ref in accepted_refs else None


@dataclass(frozen=True)
class PreparedCoverImage:
    storage_key: str
    original_name: str
    mime_type: str
    size_bytes: int


def _select_cover_candidate(
    extracted_recipe: ExtractedRecipe,
    accepted_refs: set[str],
) -> ImportCoverCandidate | None:
    candidate = extracted_recipe.cover_candidate
    if candidate is None:
        return None
    candidate_ref = _cover_candidate_ref(candidate.source_ref, accepted_refs)
    if candidate_ref is None:
        return None

    settings = get_settings()
    return anyio.run(
        choose_cover_candidate,
        CoverGuardInput(
            candidate=ImportCoverCandidate(source_ref=candidate_ref, crop=candidate.crop),
            accepted_image_refs=list(accepted_refs),
            fallback_candidates=[],
            enabled=settings.enable_cover_candidate_guard,
            max_fallback_candidates=settings.max_cover_fallback_candidates,
        ),
        None,
    )


def prepare_cover_image(
    job: ImportJobContext,
    extracted_recipe: ExtractedRecipe,
    content_recipe_resources: list[RecipeResource],
    extraction_id_by_resource: dict[RecipeResource, str],
    storage: StorageService,
) -> PreparedCoverImage | None:
    image_by_ref: dict[str, RecipeImage] = {
        extraction_id_by_resource[resource]: resource.image for resource in content_recipe_resources if resource.image is not None
    }
    chosen = _select_cover_candidate(extracted_recipe, set(image_by_ref))
    if chosen is None:
        return None

    source_image = image_by_ref[chosen.source_ref]
    cover_file = create_cover_image(
        storage,
        StorageLocation.USER_MEDIA,
        source_image.storage_key,
        context=StorageUserContext(
            owner_id=job.owner_id,
            purpose=StorageUserPurpose.IMPORT_DERIVED,
            entity_id=job.id,
        ),
        crop=chosen.crop,
        auto_crop_full_image=True,
    )
    bind_logger(
        logger,
        component=IMPORT_LOG_COMPONENT,
        owner_id=job.owner_id,
        import_job_id=job.id,
        source_ref=chosen.source_ref,
        storage_key=cover_file.storage_key,
    ).info("Cover image generated")
    return PreparedCoverImage(
        storage_key=cover_file.storage_key,
        original_name=cover_file.original_name,
        mime_type=cover_file.mime_type,
        size_bytes=cover_file.size_bytes,
    )


def attach_cover_image(
    job: ImportJobContext,
    recipe: Recipe,
    prepared: PreparedCoverImage | None,
) -> RecipeImage | None:
    if prepared is None:
        return None
    cover_image = RecipeImage(
        storage_key=prepared.storage_key,
        original_name=prepared.original_name,
        mime_type=prepared.mime_type,
        size_bytes=prepared.size_bytes,
        position=0,
    )
    recipe.images.append(cover_image)
    recipe.resources.append(
        RecipeResource(
            owner_id=job.owner_id,
            type=SourceType.IMAGE,
            source=RecipeResourceOrigin.GENERATED,
            role=RecipeResourceRole.COVER_CANDIDATE,
            image=cover_image,
            position=-1,
            status=RecipeResourceStatus.USED,
        )
    )
    recipe.cover_image = cover_image
    return cover_image
