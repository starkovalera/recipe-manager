import pytest
from pydantic import ValidationError

from app.ai.fake_provider import FakeRecipeExtractionProvider
from app.ai.schemas import ExtractedRecipe, ExtractionSource, extraction_source_id


def test_extracted_recipe_requires_quality_for_recipe_result():
    with pytest.raises(ValidationError):
        ExtractedRecipe.model_validate(
            {
                "title": "Soup",
                "ingredients": [{"name": "Water"}],
                "instructions": ["Heat water"],
            }
        )


def test_cover_candidate_accepts_source_ref_and_confidence_without_legacy_position_or_crop():
    recipe = ExtractedRecipe.model_validate(
        {
            "title": "Soup",
            "ingredients": [{"name": "Water"}],
            "instructions": ["Heat water"],
            "quality": {
                "confidence": 0.9,
                "hasConflicts": False,
                "hasIgnored": False,
                "primarySourceRefs": ["image-source"],
                "ignoredSourceRefs": [],
            },
            "coverCandidate": {"sourceRef": "image-source", "confidence": 0.8},
        }
    )

    assert recipe.coverCandidate is not None
    assert recipe.coverCandidate.sourceRef == "image-source"
    assert recipe.coverCandidate.confidence == 0.8
    assert recipe.coverCandidate.sourcePosition is None
    assert recipe.coverCandidate.crop is None


def test_cover_candidate_legacy_position_and_crop_are_none_only():
    with pytest.raises(ValidationError):
        ExtractedRecipe.model_validate(
            {
                "title": "Soup",
                "ingredients": [{"name": "Water"}],
                "instructions": ["Heat water"],
                "quality": {
                    "confidence": 0.9,
                    "hasConflicts": False,
                    "hasIgnored": False,
                    "primarySourceRefs": ["image-source"],
                    "ignoredSourceRefs": [],
                },
                "coverCandidate": {
                    "sourceRef": "image-source",
                    "confidence": 0.8,
                    "sourcePosition": 1,
                    "crop": {"x": 0, "y": 0, "width": 1, "height": 1},
                },
            }
        )


def test_extraction_source_id_matches_reference_contract():
    assert extraction_source_id(ExtractionSource(type="IMAGE", source_ref="upload_0", position=0)) == "image:upload_0"
    assert extraction_source_id(ExtractionSource(type="URL", url="https://example.test", position=1)) == "url:1"
    assert extraction_source_id(ExtractionSource(type="TEXT", text="Recipe", position=2)) == "text:2"


async def test_fake_provider_returns_not_recipe_for_empty_sources():
    provider = FakeRecipeExtractionProvider()

    result = await provider.extract([], language="ru", tags="")

    assert result.not_a_recipe is True
