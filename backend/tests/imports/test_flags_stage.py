from app.ai.schemas import ExtractedIngredient, ExtractedRecipe, ExtractionQuality
from app.imports.config import ImportConfig
from app.imports.job_context import ImportJobContext
from app.imports.job_stages.flags import set_flags
from app.models import ImportJob, ImportJobSource, Recipe, SourceType


def import_config(*, warn_confidence: float = 0.75) -> ImportConfig:
    return ImportConfig(
        max_import_images=5,
        max_import_videos=1,
        max_upload_bytes=1000,
        max_video_bytes=1000,
        max_recipe_ingredients=50,
        max_recipe_instruction_chars=1000,
        import_min_confidence=0.2,
        import_warn_confidence=warn_confidence,
    )


def job_context(*source_types: SourceType) -> ImportJobContext:
    job = ImportJob(owner_id="user-1", client_id="client-1")
    job.sources = [ImportJobSource(type=source_type, position=position) for position, source_type in enumerate(source_types)]
    return ImportJobContext.from_job(job)


def extracted_recipe(
    *,
    confidence: float = 0.9,
    has_conflicts: bool = False,
    has_ignored: bool = False,
) -> ExtractedRecipe:
    return ExtractedRecipe(
        title="Recipe",
        ingredients=[ExtractedIngredient(name="Ingredient")],
        instructions=["Cook."],
        quality=ExtractionQuality(
            confidence=confidence,
            has_conflicts=has_conflicts,
            has_ignored=has_ignored,
            primary_source_refs=["source_1"],
            ignored_source_refs=["source_2"] if has_ignored else [],
        ),
    )


def test_single_url_ignores_conflict_and_ignored_primary_for_flag_creation():
    recipe = Recipe(owner_id="user-1")
    result = extracted_recipe(has_conflicts=True, has_ignored=True)

    has_flags = set_flags(
        job_context(SourceType.URL),
        recipe,
        result,
        has_ignored_primary_resource=True,
        import_config=import_config(),
    )

    assert has_flags is False
    assert recipe.review_flags == []
    assert result.quality.has_conflicts is True
    assert result.quality.has_ignored is True


def test_single_url_low_confidence_flag_keeps_raw_quality_details():
    recipe = Recipe(owner_id="user-1")
    result = extracted_recipe(confidence=0.75, has_conflicts=True, has_ignored=True)

    has_flags = set_flags(
        job_context(SourceType.URL),
        recipe,
        result,
        has_ignored_primary_resource=True,
        import_config=import_config(),
    )

    assert has_flags is True
    assert recipe.review_flags[0].reason_code == "LOW_CONFIDENCE"
    assert recipe.review_flags[0].details == {
        "confidence": 0.75,
        "has_conflicts": True,
        "has_ignored": True,
        "primary_source_refs": ["source_1"],
        "ignored_source_refs": ["source_2"],
        "reasons": ["LOW_CONFIDENCE"],
    }


def test_multi_source_flag_includes_conflict_ignored_primary_and_low_confidence():
    recipe = Recipe(owner_id="user-1")

    has_flags = set_flags(
        job_context(SourceType.URL, SourceType.TEXT),
        recipe,
        extracted_recipe(confidence=0.7, has_conflicts=True, has_ignored=True),
        has_ignored_primary_resource=True,
        import_config=import_config(),
    )

    assert has_flags is True
    assert recipe.review_flags[0].reason_code == "CONTENT_CONFLICT"
    assert recipe.review_flags[0].details["reasons"] == [
        "CONTENT_CONFLICT",
        "IGNORED_PRIMARY_SOURCE",
        "LOW_CONFIDENCE",
    ]


def test_ignored_final_resource_without_ignored_primary_does_not_create_flag():
    recipe = Recipe(owner_id="user-1")

    has_flags = set_flags(
        job_context(SourceType.URL, SourceType.TEXT),
        recipe,
        extracted_recipe(has_ignored=True),
        has_ignored_primary_resource=False,
        import_config=import_config(),
    )

    assert has_flags is False
    assert recipe.review_flags == []
