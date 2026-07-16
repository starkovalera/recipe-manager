from app.core.config import Settings
from app.embeddings.fake_provider import FakeEmbeddingProvider
from app.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.embeddings.provider import EmbeddingProvider


def create_embedding_provider(settings: Settings) -> tuple[str, EmbeddingProvider]:
    provider = settings.embedding_provider
    if provider == "auto":
        provider = "openai" if settings.openai_api_key else "fake"
    if provider == "openai":
        return "openai", OpenAIEmbeddingProvider(settings)
    return "fake", FakeEmbeddingProvider()
