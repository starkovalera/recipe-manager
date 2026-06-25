from dataclasses import dataclass

from app.ai.schemas import ExtractionQuality


@dataclass(frozen=True)
class ImportCapacity:
    accepted_attachment_count: int
    remaining_remote_image_count: int


@dataclass(frozen=True)
class SourceAssessment:
    source_id: str
    status: str
    reason: str | None
    confidence: float | None


def attachment_first_capacity(attachment_count: int, max_images: int) -> ImportCapacity:
    accepted = min(attachment_count, max_images)
    return ImportCapacity(
        accepted_attachment_count=accepted,
        remaining_remote_image_count=max(0, max_images - accepted),
    )


def source_assessments(source_ids: list[str], quality: ExtractionQuality) -> dict[str, SourceAssessment]:
    primary = set(quality.primarySourceRefs)
    ignored = set(quality.ignoredSourceRefs)
    assessments: dict[str, SourceAssessment] = {}
    for source_id in source_ids:
        if source_id in primary:
            assessments[source_id] = SourceAssessment(
                source_id=source_id,
                status="used",
                reason="Selected as primary evidence by AI.",
                confidence=quality.confidence,
            )
        elif source_id in ignored:
            assessments[source_id] = SourceAssessment(
                source_id=source_id,
                status="ignored",
                reason="Ignored by AI when constructing the final recipe.",
                confidence=quality.confidence,
            )
        else:
            assessments[source_id] = SourceAssessment(source_id=source_id, status="unknown", reason=None, confidence=None)
    return assessments


def normalize_single_url_quality(quality: ExtractionQuality, is_single_url_import: bool) -> ExtractionQuality:
    if not is_single_url_import:
        return quality
    return quality.model_copy(update={"hasConflicts": False, "hasIgnored": False, "ignoredSourceRefs": []})


def should_create_review_flag(quality: ExtractionQuality, warn_confidence: float) -> bool:
    return quality.hasConflicts or quality.hasIgnored or quality.confidence <= warn_confidence
