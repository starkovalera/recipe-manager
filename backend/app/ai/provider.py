from typing import Protocol

from app.ai.schemas import ExtractionResult, ReadySource


class RecipeExtractionProvider(Protocol):
    async def extract(self, sources: list[ReadySource]) -> ExtractionResult:
        raise NotImplementedError
