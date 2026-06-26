from app.ai.schemas import ExtractionQuality
from app.ai.schemas import ReadySource
from app.imports.sources import (
    attachment_first_capacity,
    normalize_quality_source_refs,
    normalize_single_url_quality,
    review_reason_codes,
    source_assessments,
    should_create_review_flag,
)


def test_attachment_first_capacity_uses_remaining_space_for_url_images():
    capacity = attachment_first_capacity(attachment_count=3, max_images=5)

    assert capacity.accepted_attachment_count == 3
    assert capacity.remaining_remote_image_count == 2


def test_source_assessments_use_primary_and_ignored_refs():
    assessments = source_assessments(
        source_ids=["image:source_0", "text:1", "url:2"],
        quality=ExtractionQuality(
            confidence=0.8,
            hasConflicts=True,
            hasIgnored=True,
            primarySourceRefs=["image:source_0"],
            ignoredSourceRefs=["url:2"],
        ),
    )

    assert assessments["image:source_0"].status == "used"
    assert assessments["url:2"].status == "ignored"
    assert assessments["text:1"].status == "unknown"


def test_single_url_quality_clears_internal_conflicts():
    quality = normalize_single_url_quality(
        ExtractionQuality(
            confidence=0.9,
            hasConflicts=True,
            hasIgnored=True,
            primarySourceRefs=["url:0"],
            ignoredSourceRefs=["image:remote_0"],
        ),
        is_single_url_import=True,
    )

    assert quality.hasConflicts is False
    assert quality.hasIgnored is False
    assert quality.ignoredSourceRefs == []


def test_quality_source_refs_are_normalized_like_reference_pipeline():
    quality = normalize_quality_source_refs(
        ExtractionQuality(
            confidence=0.9,
            hasConflicts=True,
            hasIgnored=True,
            primarySourceRefs=["source_0", "https://example.com/recipe"],
            ignoredSourceRefs=["url_slide_0"],
        ),
        [
            ReadySource(type="IMAGE", sourceRef="source_0", position=0),
            ReadySource(type="URL", url="https://example.com/recipe", position=1),
            ReadySource(type="IMAGE", sourceRef="url_slide_0", position=2),
        ],
    )

    assert quality.primarySourceRefs == ["image:source_0", "url:1"]
    assert quality.ignoredSourceRefs == ["image:url_slide_0"]


def test_quality_source_refs_strip_source_id_prefix_from_ai_output():
    quality = normalize_quality_source_refs(
        ExtractionQuality(
            confidence=0.95,
            hasConflicts=False,
            hasIgnored=False,
            primarySourceRefs=["sourceId=url:0", "sourceId=image:url_slide_0"],
            ignoredSourceRefs=["sourceId=image:url_slide_1"],
        ),
        [
            ReadySource(type="URL", url="https://example.com/recipe", position=0),
            ReadySource(type="IMAGE", sourceRef="url_slide_0", position=1),
            ReadySource(type="IMAGE", sourceRef="url_slide_1", position=2),
        ],
    )

    assert quality.primarySourceRefs == ["url:0", "image:url_slide_0"]
    assert quality.ignoredSourceRefs == ["image:url_slide_1"]


def test_review_flag_thresholds_match_import_rules():
    assert should_create_review_flag(ExtractionQuality(confidence=0.75, hasConflicts=False, hasIgnored=False), 0.75)
    assert should_create_review_flag(ExtractionQuality(confidence=1, hasConflicts=True, hasIgnored=False), 0.75)
    assert should_create_review_flag(ExtractionQuality(confidence=1, hasConflicts=False, hasIgnored=True), 0.75)
    assert not should_create_review_flag(ExtractionQuality(confidence=0.9, hasConflicts=False, hasIgnored=False), 0.75)


def test_review_reason_codes_include_conflicts_ignored_and_low_confidence():
    reasons = review_reason_codes(
        ExtractionQuality(confidence=0.7, hasConflicts=True, hasIgnored=True),
        warn_confidence=0.75,
    )

    assert reasons == ["CONTENT_CONFLICT", "IGNORED_SOURCES", "LOW_CONFIDENCE"]
