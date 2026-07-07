from app.ai.schemas import ExtractionQuality, ExtractionSource
from app.imports.sources import (
    attachment_first_capacity,
    normalize_quality_source_refs,
    normalize_single_url_quality,
    review_reason_codes,
    should_create_review_flag,
    source_assessments,
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
            has_conflicts=True,
            has_ignored=True,
            primary_source_refs=["image:source_0"],
            ignored_source_refs=["url:2"],
        ),
    )

    assert assessments["image:source_0"].status == "used"
    assert assessments["url:2"].status == "ignored"
    assert assessments["text:1"].status == "unknown"


def test_single_url_quality_clears_internal_conflicts():
    quality = normalize_single_url_quality(
        ExtractionQuality(
            confidence=0.9,
            has_conflicts=True,
            has_ignored=True,
            primary_source_refs=["url:0"],
            ignored_source_refs=["image:remote_0"],
        ),
        is_single_url_import=True,
    )

    assert quality.has_conflicts is False
    assert quality.has_ignored is False
    assert quality.ignored_source_refs == []


def test_quality_source_refs_are_normalized_like_reference_pipeline():
    quality = normalize_quality_source_refs(
        ExtractionQuality(
            confidence=0.9,
            has_conflicts=True,
            has_ignored=True,
            primary_source_refs=["source_0", "https://example.com/recipe"],
            ignored_source_refs=["url_slide_0"],
        ),
        [
            ExtractionSource(type="IMAGE", source_ref="source_0", position=0),
            ExtractionSource(type="URL", url="https://example.com/recipe", position=1),
            ExtractionSource(type="IMAGE", source_ref="url_slide_0", position=2),
        ],
    )

    assert quality.primary_source_refs == ["image:source_0", "url:1"]
    assert quality.ignored_source_refs == ["image:url_slide_0"]


def test_quality_source_refs_strip_source_id_prefix_from_ai_output():
    quality = normalize_quality_source_refs(
        ExtractionQuality(
            confidence=0.95,
            has_conflicts=False,
            has_ignored=False,
            primary_source_refs=["sourceId=url:0", "sourceId=image:url_slide_0"],
            ignored_source_refs=["sourceId=image:url_slide_1"],
        ),
        [
            ExtractionSource(type="URL", url="https://example.com/recipe", position=0),
            ExtractionSource(type="IMAGE", source_ref="url_slide_0", position=1),
            ExtractionSource(type="IMAGE", source_ref="url_slide_1", position=2),
        ],
    )

    assert quality.primary_source_refs == ["url:0", "image:url_slide_0"]
    assert quality.ignored_source_refs == ["image:url_slide_1"]


def test_quality_source_refs_normalize_bare_positions_from_ai_output():
    quality = normalize_quality_source_refs(
        ExtractionQuality(
            confidence=0.95,
            has_conflicts=False,
            has_ignored=False,
            primary_source_refs=["0", "1", "url_video_poster_0"],
            ignored_source_refs=[],
        ),
        [
            ExtractionSource(type="URL", url="https://example.com/recipe", position=0),
            ExtractionSource(type="TEXT", text="Video transcript", position=1),
            ExtractionSource(type="IMAGE", source_ref="url_video_poster_0", position=2),
        ],
    )

    assert quality.primary_source_refs == ["url:0", "text:1", "image:url_video_poster_0"]


def test_review_flag_thresholds_match_import_rules():
    assert should_create_review_flag(ExtractionQuality(confidence=0.75, has_conflicts=False, has_ignored=False), 0.75)
    assert should_create_review_flag(ExtractionQuality(confidence=1, has_conflicts=True, has_ignored=False), 0.75)
    assert should_create_review_flag(ExtractionQuality(confidence=1, has_conflicts=False, has_ignored=True), 0.75)
    assert not should_create_review_flag(ExtractionQuality(confidence=0.9, has_conflicts=False, has_ignored=False), 0.75)


def test_review_reason_codes_include_conflicts_ignored_and_low_confidence():
    reasons = review_reason_codes(
        ExtractionQuality(confidence=0.7, has_conflicts=True, has_ignored=True),
        warn_confidence=0.75,
    )

    assert reasons == ["CONTENT_CONFLICT", "IGNORED_SOURCES", "LOW_CONFIDENCE"]
