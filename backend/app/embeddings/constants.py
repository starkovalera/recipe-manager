from enum import StrEnum


class EmbeddingProcessingDisposition(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    NOOP = "NOOP"
    REQUEUED = "REQUEUED"
    BUSY = "BUSY"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"


EMBEDDING_LOG_COMPONENT = "recipes.embeddings"

EMBEDDING_DIMENSIONS = 1536
