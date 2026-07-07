from dataclasses import dataclass

from app.ai.schemas import ExtractionQuality, ExtractionSource, extraction_source_id


@dataclass(frozen=True)
class ImportCapacity:
    # Runtime capacity is currently computed inline from RawSource state
    # because URL images and video poster images consume the same remaining
    # image budget. This value object is kept as an executable invariant for
    # the attachments-first rule.
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
    primary = set(quality.primary_source_refs)
    ignored = set(quality.ignored_source_refs)
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
    return quality.model_copy(update={"has_conflicts": False, "has_ignored": False, "ignored_source_refs": []})


def normalize_quality_source_refs(quality: ExtractionQuality, sources: list[ExtractionSource]) -> ExtractionQuality:
    aliases: dict[str, str] = {}
    for source in sources:
        canonical = extraction_source_id(source)
        aliases[canonical] = canonical
        aliases[str(source.position)] = canonical
        if source.type == "IMAGE" and source.source_ref:
            aliases[source.source_ref] = canonical
            aliases[f"image:{source.source_ref}"] = canonical
        elif source.type == "URL" and source.url:
            aliases[source.url] = canonical

    def normalize(source_ref: str) -> str:
        value = source_ref.strip()
        if value.startswith("sourceId="):
            value = value.removeprefix("sourceId=").strip()
        return aliases.get(value, value)

    return quality.model_copy(
        update={
            "primary_source_refs": [normalize(source_ref) for source_ref in quality.primary_source_refs],
            "ignored_source_refs": [normalize(source_ref) for source_ref in quality.ignored_source_refs],
        }
    )


def should_create_review_flag(quality: ExtractionQuality, warn_confidence: float) -> bool:
    # Kept for the generic AI-quality rule and its unit tests. Production import
    # creation uses should_create_primary_review_flag because ignored final
    # resources must first be aggregated back to primary resources.
    return quality.has_conflicts or quality.has_ignored or quality.confidence <= warn_confidence


def should_create_primary_review_flag(quality: ExtractionQuality, warn_confidence: float, has_ignored_primary: bool) -> bool:
    return quality.has_conflicts or has_ignored_primary or quality.confidence <= warn_confidence


def review_reason_codes(quality: ExtractionQuality, warn_confidence: float, has_ignored_primary: bool | None = None) -> list[str]:
    reasons: list[str] = []
    if quality.has_conflicts:
        reasons.append("CONTENT_CONFLICT")
    if has_ignored_primary is True:
        reasons.append("IGNORED_PRIMARY_SOURCE")
    elif has_ignored_primary is None and quality.has_ignored:
        reasons.append("IGNORED_SOURCES")
    if quality.confidence <= warn_confidence:
        reasons.append("LOW_CONFIDENCE")
    return reasons
