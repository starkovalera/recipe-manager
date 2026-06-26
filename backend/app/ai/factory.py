from app.ai.fake_provider import FakeRecipeExtractionProvider
from app.ai.openai_provider import OpenAIRecipeExtractionProvider
from app.ai.provider import RecipeExtractionProvider
from app.core.config import Settings


def create_recipe_extraction_provider(settings: Settings) -> tuple[str, RecipeExtractionProvider]:
    provider = settings.ai_provider
    if provider == "auto":
        provider = "openai" if settings.openai_api_key else "fake"
    if provider == "openai":
        return "openai", OpenAIRecipeExtractionProvider(settings)
    return "fake", FakeRecipeExtractionProvider()
