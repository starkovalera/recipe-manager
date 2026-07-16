from app.core.config import get_settings
from app.embeddings.factory import create_embedding_provider
from app.embeddings.provider import EmbeddingProvider


def get_embedding_provider() -> tuple[str, EmbeddingProvider]:
    return create_embedding_provider(get_settings())
