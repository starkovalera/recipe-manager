import logging

from app.ai.schemas import ExtractedRecipe, ExtractionQuality
from app.core.logging import bind_logger
from app.imports.config import ImportConfig
from app.imports.constants import IMPORT_LOG_COMPONENT
from app.imports.job_context import ImportJobContext
from app.models import (
    Recipe,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    RecipeReviewFlagType,
)

logger = logging.getLogger(IMPORT_LOG_COMPONENT)


def set_flags(
    job: ImportJobContext,
    recipe: Recipe,
    extracted_recipe: ExtractedRecipe,
    has_ignored_primary_resource: bool,
    import_config: ImportConfig,
) -> bool:
    flag_reasons = _review_reason_codes(
        extracted_recipe.quality,
        import_config.import_warn_confidence,
        has_ignored_primary_resource,
        job.is_single_url_import,
    )
    if not flag_reasons:
        return False

    recipe.review_flags.append(
        RecipeReviewFlag(
            owner_id=job.owner_id,
            type=RecipeReviewFlagType.CONTENT_WARNING,
            status=RecipeReviewFlagStatus.OPEN,
            reason_code=flag_reasons[0],
            message=f"Review suggested: {', '.join(flag_reasons)}.",
            details={**extracted_recipe.quality.model_dump(), "reasons": flag_reasons},
        )
    )
    bind_logger(
        logger,
        owner_id=job.owner_id,
        import_job_id=job.id,
        reason_codes=flag_reasons,
        confidence=extracted_recipe.quality.confidence,
        has_conflicts=extracted_recipe.quality.has_conflicts,
        has_ignored=extracted_recipe.quality.has_ignored,
    ).info("Recipe review flag created.")
    return True


def _review_reason_codes(
    quality: ExtractionQuality,
    warn_confidence: float,
    has_ignored_primary: bool,
    is_single_url_import: bool,
) -> list[str]:
    reasons: list[str] = []
    if not is_single_url_import:
        if quality.has_conflicts:
            reasons.append("CONTENT_CONFLICT")
        if has_ignored_primary:
            reasons.append("IGNORED_PRIMARY_SOURCE")
    if quality.confidence <= warn_confidence:
        reasons.append("LOW_CONFIDENCE")
    return reasons
