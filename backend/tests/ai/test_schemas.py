import pytest
from pydantic import ValidationError

from app.ai.fake_provider import FakeRecipeExtractionProvider
from app.ai.schemas import ExtractedRecipe, ReadySource, ready_source_id


def test_extracted_recipe_requires_quality_for_recipe_result():
    with pytest.raises(ValidationError):
        ExtractedRecipe.model_validate(
            {
                "title": "Soup",
                "ingredients": [{"name": "Water"}],
                "instructions": ["Heat water"],
            }
        )


def test_ready_source_id_matches_reference_contract():
    assert ready_source_id(ReadySource(type="IMAGE", sourceRef="upload_0", position=0)) == "image:upload_0"
    assert ready_source_id(ReadySource(type="URL", url="https://example.test", position=1)) == "url:1"
    assert ready_source_id(ReadySource(type="TEXT", text="Recipe", position=2)) == "text:2"


async def test_fake_provider_returns_not_recipe_for_empty_sources():
    provider = FakeRecipeExtractionProvider()

    result = await provider.extract([])

    assert result.not_a_recipe is True
