from dataclasses import dataclass

from app.ai.schemas import ExtractionQuality
from app.imports.source_platform import derive_source_name
from app.models import (
    Recipe,
    RecipeResource,
    RecipeResourceOrigin,
    RecipeResourceStatus,
    SourceName,
    SourceType,
)


@dataclass(frozen=True)
class SourceAssessment:
    source_id: str
    status: str
    reason: str | None
    confidence: float | None


def build_recipe_resources(
    recipe: Recipe,
    recipe_resources: list[RecipeResource],
    content_recipe_resources: list[RecipeResource],
    extraction_id_by_resource: dict[RecipeResource, str],
    extracted_quality: ExtractionQuality,
) -> bool:
    has_ignored_primary_resource = _build_resource_statuses(
        recipe_resources,
        content_recipe_resources,
        extraction_id_by_resource,
        extracted_quality,
    )
    recipe.source_name = _source_name_from_primary_resources(recipe_resources)
    return has_ignored_primary_resource


def _build_resource_statuses(
    recipe_resources: list[RecipeResource],
    content_recipe_resources: list[RecipeResource],
    extraction_id_by_resource: dict[RecipeResource, str],
    extracted_quality: ExtractionQuality,
) -> bool:
    """Returns if there is an ignored primary resource among the passed."""
    assessments = _source_assessments([extraction_id_by_resource[resource] for resource in content_recipe_resources], extracted_quality)
    for resource in content_recipe_resources:
        assessment = assessments[extraction_id_by_resource[resource]]
        resource.status = RecipeResourceStatus(assessment.status)
        resource.assessment_reason = assessment.reason
        resource.assessment_confidence = assessment.confidence

    for resource in recipe_resources:
        # primary resources definition
        if resource.parent is not None or resource.type != SourceType.URL:
            continue
        children = [child for child in recipe_resources if child.parent is resource]
        if any(child.status == RecipeResourceStatus.USED for child in children):
            resource.status = RecipeResourceStatus.USED
            resource.assessment_reason = "At least one child resource was selected as primary evidence by the extractor."
            resource.assessment_confidence = extracted_quality.confidence
        elif children and all(child.status == RecipeResourceStatus.IGNORED for child in children):
            resource.status = RecipeResourceStatus.IGNORED
            resource.assessment_reason = "All child resources were ignored by the extractor."
            resource.assessment_confidence = extracted_quality.confidence
        else:
            resource.status = RecipeResourceStatus.UNKNOWN
            resource.assessment_reason = None
            resource.assessment_confidence = None

    return any(resource.parent is None and resource.status == RecipeResourceStatus.IGNORED for resource in recipe_resources)


def _source_name_from_primary_resources(resources: list[RecipeResource]) -> SourceName:
    primary_resources = [
        resource
        for resource in resources
        if resource.parent is None and resource.status not in {RecipeResourceStatus.IGNORED, RecipeResourceStatus.DELETED}
    ]
    url_values = [resource.url for resource in primary_resources if resource.type == SourceType.URL and resource.url]
    if url_values:
        result = derive_source_name(url_values)
        return result.source_name if result.ok and result.source_name is not None else SourceName.OTHER
    if any(
        resource.source == RecipeResourceOrigin.MANUAL and resource.type in {SourceType.IMAGE, SourceType.TEXT}
        for resource in primary_resources
    ):
        return SourceName.MANUAL
    return SourceName.OTHER


def _source_assessments(source_ids: list[str], quality: ExtractionQuality) -> dict[str, SourceAssessment]:
    primary = set(quality.primary_source_refs)
    ignored = set(quality.ignored_source_refs)
    assessments: dict[str, SourceAssessment] = {}
    for source_id in source_ids:
        if source_id in primary:
            assessments[source_id] = SourceAssessment(
                source_id=source_id,
                status="used",
                reason="Selected as primary evidence by the extractor.",
                confidence=quality.confidence,
            )
        elif source_id in ignored:
            assessments[source_id] = SourceAssessment(
                source_id=source_id,
                status="ignored",
                reason="Ignored by the extractor when constructing the final recipe.",
                confidence=quality.confidence,
            )
        else:
            assessments[source_id] = SourceAssessment(
                source_id=source_id,
                status="unknown",
                reason=None,
                confidence=None,
            )
    return assessments
