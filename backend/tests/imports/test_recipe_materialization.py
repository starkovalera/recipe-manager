from app.ai.schemas import ExtractedIngredient, ExtractedRecipe, ExtractionQuality
from app.imports.recipe_materialization import create_review_flag_if_needed
from app.models import ImportJob, ImportJobSource, Recipe, SourceType


def extracted_recipe_with_quality(quality: ExtractionQuality) -> ExtractedRecipe:
    return ExtractedRecipe(
        title="Recipe",
        ingredients=[ExtractedIngredient(name="Ingredient")],
        instructions=["Cook."],
        quality=quality,
    )


def import_job_with_sources(*source_types: SourceType) -> ImportJob:
    job = ImportJob(owner_id="user-1", client_id="client-1")
    job.sources = [ImportJobSource(type=source_type, position=index) for index, source_type in enumerate(source_types)]
    return job


def test_single_url_ignored_primary_does_not_create_review_flag():
    recipe = Recipe(owner_id="user-1")
    recipe_result = extracted_recipe_with_quality(
        ExtractionQuality(
            confidence=0.9,
            has_conflicts=False,
            has_ignored=False,
            primary_source_refs=["source_1"],
            ignored_source_refs=[],
        )
    )

    has_review_flag = create_review_flag_if_needed(
        import_job_with_sources(SourceType.URL),
        recipe,
        recipe_result,
        has_ignored_primary=True,
    )

    assert has_review_flag is False
    assert recipe.review_flags == []


def test_single_url_conflict_does_not_create_review_flag_after_quality_normalization():
    recipe = Recipe(owner_id="user-1")
    recipe_result = extracted_recipe_with_quality(
        ExtractionQuality(
            confidence=0.9,
            has_conflicts=False,
            has_ignored=False,
            primary_source_refs=["source_1"],
            ignored_source_refs=[],
        )
    )

    has_review_flag = create_review_flag_if_needed(
        import_job_with_sources(SourceType.URL),
        recipe,
        recipe_result,
        has_ignored_primary=False,
    )

    assert has_review_flag is False
    assert recipe.review_flags == []


def test_single_url_low_confidence_creates_review_flag():
    recipe = Recipe(owner_id="user-1")
    recipe_result = extracted_recipe_with_quality(
        ExtractionQuality(
            confidence=0.7,
            has_conflicts=False,
            has_ignored=False,
            primary_source_refs=["source_1"],
            ignored_source_refs=[],
        )
    )

    has_review_flag = create_review_flag_if_needed(
        import_job_with_sources(SourceType.URL),
        recipe,
        recipe_result,
        has_ignored_primary=True,
    )

    assert has_review_flag is True
    assert recipe.review_flags[0].reason_code == "LOW_CONFIDENCE"


def test_multi_primary_ignored_primary_creates_review_flag():
    recipe = Recipe(owner_id="user-1")
    recipe_result = extracted_recipe_with_quality(
        ExtractionQuality(
            confidence=0.9,
            has_conflicts=False,
            has_ignored=False,
            primary_source_refs=["source_1"],
            ignored_source_refs=[],
        )
    )

    has_review_flag = create_review_flag_if_needed(
        import_job_with_sources(SourceType.URL, SourceType.TEXT),
        recipe,
        recipe_result,
        has_ignored_primary=True,
    )

    assert has_review_flag is True
    assert recipe.review_flags[0].reason_code == "IGNORED_PRIMARY_SOURCE"
