import pytest

from app.ai.schemas import ExtractedIngredient, ExtractedRecipe, ExtractionQuality, ExtractionSource
from app.imports.config import ImportConfig
from app.imports.error_codes import NotARecipeError, RecipeTooLongError
from app.imports.job_stages.extracted_recipe import normalize_extracted_recipe, validate_extracted_recipe


def import_config(*, min_confidence: float = 0.2, max_ingredients: int = 50, max_instruction_chars: int = 1000) -> ImportConfig:
    return ImportConfig(
        max_import_images=5,
        max_import_videos=1,
        max_upload_bytes=1000,
        max_video_bytes=1000,
        max_recipe_ingredients=max_ingredients,
        max_recipe_instruction_chars=max_instruction_chars,
        import_min_confidence=min_confidence,
        import_warn_confidence=0.75,
    )


def extracted_recipe(*, confidence: float = 0.9, has_conflicts: bool = True, has_ignored: bool = True) -> ExtractedRecipe:
    return ExtractedRecipe(
        title="Recipe",
        ingredients=[ExtractedIngredient(name="Ingredient")],
        instructions=["Cook."],
        quality=ExtractionQuality(
            confidence=confidence,
            has_conflicts=has_conflicts,
            has_ignored=has_ignored,
            primary_source_refs=["sourceId=source_1"],
            ignored_source_refs=["sourceId=source_2"],
        ),
    )


def test_validate_extracted_recipe_rejects_low_confidence():
    with pytest.raises(NotARecipeError) as exc_info:
        validate_extracted_recipe(extracted_recipe(confidence=0.1), import_config(min_confidence=0.2))

    assert exc_info.value.extra == {"confidence": 0.1}


def test_validate_extracted_recipe_rejects_oversized_recipe():
    with pytest.raises(RecipeTooLongError) as exc_info:
        validate_extracted_recipe(extracted_recipe(), import_config(max_ingredients=0))

    assert exc_info.value.extra == {"reason": "too_many_ingredients", "actual": 1, "limit": 0}


def test_normalize_extracted_recipe_canonicalizes_source_refs():
    result = normalize_extracted_recipe(
        extracted_recipe(),
        [
            ExtractionSource(id="source_1", type="TEXT", position=0, text="Recipe text"),
            ExtractionSource(id="source_2", type="IMAGE", position=1, source_ref="image_1"),
        ],
    )

    assert result.quality.primary_source_refs == ["source_1"]
    assert result.quality.ignored_source_refs == ["source_2"]


def test_normalize_extracted_recipe_preserves_quality_flags():
    result = normalize_extracted_recipe(
        extracted_recipe(has_conflicts=True, has_ignored=True),
        [
            ExtractionSource(id="source_1", type="TEXT", position=0, text="Recipe text"),
            ExtractionSource(id="source_2", type="IMAGE", position=1, source_ref="image_1"),
        ],
    )

    assert result.quality.has_conflicts is True
    assert result.quality.has_ignored is True
    assert result.quality.primary_source_refs == ["source_1"]
    assert result.quality.ignored_source_refs == ["source_2"]
