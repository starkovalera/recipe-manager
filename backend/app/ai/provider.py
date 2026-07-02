from typing import Protocol

from app.ai.schemas import ExtractionResult, ReadySource


class RecipeExtractionProvider(Protocol):
    async def extract(self, sources: list[ReadySource], *, language: str, tags: str) -> ExtractionResult:
        raise NotImplementedError
