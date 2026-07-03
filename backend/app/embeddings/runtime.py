from app.core.config import get_settings
from app.embeddings.factory import create_embedding_provider
from app.embeddings.provider import EmbeddingProvider

_embedding_provider_override: EmbeddingProvider | None = None


def get_embedding_provider() -> tuple[str, EmbeddingProvider]:
    if _embedding_provider_override is not None:
        return "test", _embedding_provider_override
    return create_embedding_provider(get_settings())
