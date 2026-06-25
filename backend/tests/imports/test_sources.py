from app.ai.schemas import ExtractionQuality
from app.imports.sources import (
    attachment_first_capacity,
    normalize_single_url_quality,
    source_assessments,
    should_create_review_flag,
)


def test_attachment_first_capacity_uses_remaining_space_for_url_images():
    capacity = attachment_first_capacity(attachment_count=3, max_images=5)

    assert capacity.accepted_attachment_count == 3
    assert capacity.remaining_remote_image_count == 2


def test_source_assessments_use_primary_and_ignored_refs():
    assessments = source_assessments(
        source_ids=["image:upload_0", "text:1", "url:2"],
        quality=ExtractionQuality(
            confidence=0.8,
            hasConflicts=True,
            hasIgnored=True,
            primarySourceRefs=["image:upload_0"],
            ignoredSourceRefs=["url:2"],
        ),
    )

    assert assessments["image:upload_0"].status == "used"
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


def test_review_flag_thresholds_match_import_rules():
    assert should_create_review_flag(ExtractionQuality(confidence=0.75, hasConflicts=False, hasIgnored=False), 0.75)
    assert should_create_review_flag(ExtractionQuality(confidence=1, hasConflicts=True, hasIgnored=False), 0.75)
    assert not should_create_review_flag(ExtractionQuality(confidence=0.9, hasConflicts=False, hasIgnored=False), 0.75)
