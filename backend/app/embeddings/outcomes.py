from dataclasses import dataclass

from app.embeddings.constants import EmbeddingProcessingDisposition


@dataclass(frozen=True)
class EmbeddingProcessingResult:
    recipe_id: str
    disposition: EmbeddingProcessingDisposition
    failed_attempts: int | None = None
