import dramatiq

from app.core.config import get_settings
from app.core.dramatiq import broker as _broker  # noqa: F401
from app.embeddings.outcomes import EmbeddingProcessingDisposition
from app.embeddings.processing import process_recipe_embedding

RETRYABLE_DISPOSITIONS = {
    EmbeddingProcessingDisposition.BUSY,
    EmbeddingProcessingDisposition.RETRYABLE_FAILURE,
}


class RetryableEmbeddingTaskError(RuntimeError):
    pass


@dramatiq.actor(max_retries=get_settings().embedding_task_max_retries)
def embed_recipe_task(recipe_id: str) -> None:
    result = process_recipe_embedding(recipe_id)
    if result.disposition in RETRYABLE_DISPOSITIONS:
        raise RetryableEmbeddingTaskError(
            f"Embedding processing returned retryable disposition {result.disposition.value}."
        )
