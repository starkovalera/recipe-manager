import logging

from app.ai.schemas import ExtractedRecipe, ReadySource
from app.core.config import get_settings
from app.core.logging import bind_logger
from app.imports.constants import IMPORT_LOG_COMPONENT, IMPORT_LOG_PREFIX
from app.imports.error_codes import ImportExtractionError, ImportExtractionErrorCode
from app.imports.source_platform import derive_source_name
from app.imports.sources import (
    normalize_quality_source_refs,
    normalize_single_url_quality,
    review_reason_codes,
    should_create_primary_review_flag,
    source_assessments,
)
from app.models import (
    ImportJob,
    Ingredient,
    Recipe,
    RecipeResource,
    RecipeResourceOrigin,
    RecipeResourceStatus,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    RecipeReviewFlagType,
    SourceName,
    SourceType,
    Tag,
)
from app.services.recipe_limits import find_recipe_size_violation
from app.services.search_text import build_ingredient_search_name

logger = logging.getLogger(IMPORT_LOG_COMPONENT)


def normalize_recipe_result(job: ImportJob, recipe_result: ExtractedRecipe, ready_sources: list[ReadySource]):
    size_violation = find_recipe_size_violation(recipe_result.ingredients, recipe_result.instructions)
    if size_violation is not None:
        raise ImportExtractionError(
            ImportExtractionErrorCode.RECIPE_TOO_LONG,
            diagnostic_message=size_violation.reason,
            payload={"reason": size_violation.reason, "actual": size_violation.actual, "limit": size_violation.limit},
        )
    is_single_url_import = len(job.sources) == 1 and job.sources[0].type == SourceType.URL
    status_quality = normalize_quality_source_refs(recipe_result.quality, ready_sources)
    recipe_quality = normalize_single_url_quality(status_quality, is_single_url_import)
    return recipe_result.model_copy(update={"quality": recipe_quality}), status_quality


def apply_extracted_recipe(
    recipe: Recipe,
    recipe_result: ExtractedRecipe,
    *,
    active_tags: list[Tag],
    imported_author_name: str | None,
    owner_id: str,
    import_job_id: str,
) -> None:
    recipe.title = recipe_result.title
    recipe.instructions = recipe_result.instructions
    recipe.servings = recipe_result.servings
    recipe.cook_time_minutes = recipe_result.cookTimeMinutes
    recipe.nutrition_estimate = recipe_result.nutritionEstimate.model_dump() if recipe_result.nutritionEstimate else None
    recipe.author_name = recipe_result.authorName or imported_author_name
    _attach_ai_tags(recipe, active_tags, recipe_result.tags, owner_id, import_job_id)
    for index, ingredient in enumerate(recipe_result.ingredients):
        recipe.ingredients.append(
            Ingredient(
                name=ingredient.name,
                search_name=build_ingredient_search_name(ingredient.name),
                quantity=ingredient.quantity,
                unit=ingredient.unit,
                note=ingredient.note,
                position=index,
            )
        )


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


def create_review_flag_if_needed(job: ImportJob, recipe: Recipe, recipe_result: ExtractedRecipe, has_ignored_primary: bool) -> bool:
    warn_confidence = get_settings().import_warn_confidence
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
        ownerId=job.owner_id,
        importJobId=job.id,
        reasonCodes=reasons,
        confidence=recipe_result.quality.confidence,
        hasConflicts=recipe_result.quality.hasConflicts,
        hasIgnored=recipe_result.quality.hasIgnored,
    ).info(f"{IMPORT_LOG_PREFIX} Recipe review flag created")
    return True


def _normalize_tag_name(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _attach_ai_tags(recipe: Recipe, active_tags: list[Tag], ai_tags: list[str], owner_id: str, import_job_id: str) -> None:
    tag_by_name = {_normalize_tag_name(tag.name): tag for tag in active_tags}
    matched_tags: list[Tag] = []
    seen: set[str] = set()
    ignored_tags: list[str] = []
    duplicate_tags: list[str] = []
    for ai_tag in ai_tags:
        normalized = _normalize_tag_name(ai_tag)
        tag = tag_by_name.get(normalized)
        if tag is None:
            ignored_tags.append(ai_tag)
            continue
        if normalized in seen:
            duplicate_tags.append(ai_tag)
            continue
        matched_tags.append(tag)
        seen.add(normalized)
    recipe.tags = matched_tags
    bind_logger(
        logger,
        component=IMPORT_LOG_COMPONENT,
        ownerId=owner_id,
        importJobId=import_job_id,
        returnedCount=len(ai_tags),
        duplicateCount=len(duplicate_tags),
        duplicateTags=duplicate_tags,
        validCount=len(matched_tags),
        validTags=[tag.name for tag in matched_tags],
        invalidCount=len(ignored_tags),
        invalidTags=ignored_tags,
    ).info(f"{IMPORT_LOG_PREFIX} AI tags processed")
