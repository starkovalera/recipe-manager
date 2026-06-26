from dataclasses import dataclass

from app.ai.schemas import ExtractionQuality, ReadySource, ready_source_id


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


def normalize_quality_source_refs(quality: ExtractionQuality, sources: list[ReadySource]) -> ExtractionQuality:
    aliases: dict[str, str] = {}
    for source in sources:
        canonical = ready_source_id(source)
        aliases[canonical] = canonical
        if source.type == "IMAGE" and source.sourceRef:
            aliases[source.sourceRef] = canonical
            aliases[f"image:{source.sourceRef}"] = canonical
        elif source.type == "URL" and source.url:
            aliases[source.url] = canonical

    def normalize(source_ref: str) -> str:
        return aliases.get(source_ref, source_ref)

    return quality.model_copy(
        update={
            "primarySourceRefs": [normalize(source_ref) for source_ref in quality.primarySourceRefs],
            "ignoredSourceRefs": [normalize(source_ref) for source_ref in quality.ignoredSourceRefs],
        }
    )


def should_create_review_flag(quality: ExtractionQuality, warn_confidence: float) -> bool:
    return quality.hasConflicts or quality.hasIgnored or quality.confidence <= warn_confidence


def review_reason_codes(quality: ExtractionQuality, warn_confidence: float) -> list[str]:
    reasons: list[str] = []
    if quality.hasConflicts:
        reasons.append("CONTENT_CONFLICT")
    if quality.hasIgnored:
        reasons.append("IGNORED_SOURCES")
    if quality.confidence <= warn_confidence:
        reasons.append("LOW_CONFIDENCE")
    return reasons
