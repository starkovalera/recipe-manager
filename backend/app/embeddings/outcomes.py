from dataclasses import dataclass
from enum import StrEnum


class EmbeddingProcessingDisposition(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    NOOP = "NOOP"
    REQUEUED = "REQUEUED"
    BUSY = "BUSY"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"


@dataclass(frozen=True)
class EmbeddingProcessingResult:
    recipe_id: str
    disposition: EmbeddingProcessingDisposition
    failed_attempts: int | None = None
