import logging
from dataclasses import dataclass

import anyio

from app.ai.schemas import ExtractedRecipe
from app.core.config import get_settings
from app.core.logging import bind_logger
from app.imports.constants import IMPORT_LOG_COMPONENT
from app.imports.cover_guard import CoverCandidate as ImportCoverCandidate, CoverGuardInput, choose_cover_candidate
from app.media.images import create_cover_image
from app.models import (
    ImportJob,
    Recipe,
    RecipeImage,
    RecipeResource,
    RecipeResourceOrigin,
    RecipeResourceRole,
    RecipeResourceStatus,
    SourceType,
)
from app.storage.base import StorageService

logger = logging.getLogger(IMPORT_LOG_COMPONENT)


@dataclass
class CoverGenerationContext:
    storage: StorageService
    saved_storage_keys: list[str]
    final_resources: list[RecipeResource]
    ai_id_by_resource: dict[RecipeResource, str]


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


def generate_cover_image(
    job: ImportJob,
    recipe: Recipe,
    recipe_result: ExtractedRecipe,
    context: CoverGenerationContext,
) -> RecipeImage | None:
    image_by_ref: dict[str, RecipeImage] = {
        context.ai_id_by_resource[resource]: resource.image
        for resource in context.final_resources
        if resource.image is not None
    }
    candidate_ref = _cover_candidate_ref(
        recipe_result.coverCandidate.sourceRef if recipe_result.coverCandidate else None,
        set(image_by_ref.keys()),
    )
    if candidate_ref is None or recipe_result.coverCandidate is None:
        return None

    chosen = anyio.run(
        choose_cover_candidate,
        CoverGuardInput(
            candidate=ImportCoverCandidate(sourceRef=candidate_ref, crop=recipe_result.coverCandidate.crop),
            acceptedImageRefs=list(image_by_ref.keys()),
            fallbackCandidates=[],
            enabled=get_settings().enable_cover_candidate_guard,
            maxFallbackCandidates=get_settings().max_cover_fallback_candidates,
        ),
        None,
    )
    if chosen is None:
        return None

    source_image = image_by_ref[chosen.sourceRef]
    cover_file = create_cover_image(context.storage, source_image.storage_key, chosen.crop, auto_crop_full_image=True)
    context.saved_storage_keys.append(cover_file.storage_key)
    cover_image = RecipeImage(
        storage_key=cover_file.storage_key,
        original_name=cover_file.original_name,
        mime_type=cover_file.mime_type,
        size_bytes=cover_file.size_bytes,
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
    bind_logger(
        logger,
        component=IMPORT_LOG_COMPONENT,
        owner_id=job.owner_id,
        import_job_id=job.id,
        source_ref=chosen.sourceRef,
        storage_key=cover_file.storage_key,
    ).info(f"{IMPORT_LOG_COMPONENT} Cover image generated")
    return cover_image
