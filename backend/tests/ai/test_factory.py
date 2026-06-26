from app.ai.factory import create_recipe_extraction_provider
from app.ai.fake_provider import FakeRecipeExtractionProvider
from app.ai.openai_provider import OpenAIRecipeExtractionProvider
from app.core.config import Settings


def test_auto_provider_uses_fake_without_openai_key():
    name, provider = create_recipe_extraction_provider(Settings(ai_provider="auto", openai_api_key=None))

    assert name == "fake"
    assert isinstance(provider, FakeRecipeExtractionProvider)


def test_openai_provider_is_selected_when_configured():
    name, provider = create_recipe_extraction_provider(Settings(ai_provider="openai", openai_api_key="test-key"))

    assert name == "openai"
    assert isinstance(provider, OpenAIRecipeExtractionProvider)
