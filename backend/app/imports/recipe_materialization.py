import logging

from app.ai.schemas import ExtractedRecipe
from app.core.config import get_settings
from app.core.logging import bind_logger
from app.imports.constants import IMPORT_LOG_COMPONENT
from app.imports.job_context import ImportJobContext
from app.imports.source_platform import derive_source_name
from app.imports.sources import (
    review_reason_codes,
    should_create_primary_review_flag,
    source_assessments,
)
from app.models import (
    Recipe,
    RecipeResource,
    RecipeResourceOrigin,
    RecipeResourceStatus,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    RecipeReviewFlagType,
    SourceName,
    SourceType,
)

logger = logging.getLogger(IMPORT_LOG_COMPONENT)


def apply_source_statuses(
    recipe_resources: list[RecipeResource],
    final_resources: list[RecipeResource],
    quality,
    ai_id_by_resource: dict[RecipeResource, str],
) -> bool:
    assessments = source_assessments([ai_id_by_resource[resource] for resource in final_resources], quality)
    for resource in final_resources:
        assessment = assessments[ai_id_by_resource[resource]]
        resource.status = RecipeResourceStatus(assessment.status)
        resource.assessment_reason = assessment.reason
        resource.assessment_confidence = assessment.confidence

    for resource in recipe_resources:
        if resource.parent is not None or resource.type != SourceType.URL:
            continue
        children = [child for child in recipe_resources if child.parent is resource]
        if not children:
            resource.status = RecipeResourceStatus.UNKNOWN
        elif any(child.status == RecipeResourceStatus.USED for child in children):
            resource.status = RecipeResourceStatus.USED
            resource.assessment_reason = "At least one child resource was selected as primary evidence by AI."
            resource.assessment_confidence = quality.confidence
        elif all(child.status == RecipeResourceStatus.IGNORED for child in children):
            resource.status = RecipeResourceStatus.IGNORED
            resource.assessment_reason = "All child resources were ignored by AI."
            resource.assessment_confidence = quality.confidence
        else:
            resource.status = RecipeResourceStatus.UNKNOWN
            resource.assessment_reason = None
            resource.assessment_confidence = None

    return any(resource.parent is None and resource.status == RecipeResourceStatus.IGNORED for resource in recipe_resources)


def derive_source_name_from_primary_resources(resources: list[RecipeResource]) -> SourceName:
    primary_resources = [
        resource
        for resource in resources
        if resource.parent is None and resource.status not in {RecipeResourceStatus.IGNORED, RecipeResourceStatus.DELETED}
    ]
    url_values = [resource.url for resource in primary_resources if resource.type == SourceType.URL and resource.url]
    if url_values:
        result = derive_source_name(url_values)
        return result.source_name if result.ok and result.source_name is not None else SourceName.OTHER
    if any(resource.source == RecipeResourceOrigin.MANUAL and resource.type in {SourceType.IMAGE, SourceType.TEXT} for resource in primary_resources):
        return SourceName.MANUAL
    return SourceName.OTHER


def create_review_flag_if_needed(
    job: ImportJobContext,
    recipe: Recipe,
    recipe_result: ExtractedRecipe,
    has_ignored_primary: bool,
) -> bool:
    warn_confidence = get_settings().import_warn_confidence
    if job.is_single_url_import:
        has_ignored_primary = False
    reasons = review_reason_codes(recipe_result.quality, warn_confidence, has_ignored_primary)
    has_review_flag = should_create_primary_review_flag(recipe_result.quality, warn_confidence, has_ignored_primary)
    if not has_review_flag:
        return False

    recipe.review_flags.append(
        RecipeReviewFlag(
            owner_id=job.owner_id,
            type=RecipeReviewFlagType.CONTENT_WARNING,
            status=RecipeReviewFlagStatus.OPEN,
            reason_code=reasons[0],
            message=f"Review suggested: {', '.join(reasons)}.",
            details={**recipe_result.quality.model_dump(), "reasons": reasons},
        )
    )
    bind_logger(
        logger,
        component=IMPORT_LOG_COMPONENT,
        owner_id=job.owner_id,
        import_job_id=job.id,
        reason_codes=reasons,
        confidence=recipe_result.quality.confidence,
        has_conflicts=recipe_result.quality.has_conflicts,
        has_ignored=recipe_result.quality.has_ignored,
    ).info(f"{IMPORT_LOG_COMPONENT} Recipe review flag created")
    return True
