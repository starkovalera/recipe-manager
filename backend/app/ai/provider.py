from typing import Protocol

from app.ai.schemas import ExtractionResult, ExtractionSource


class RecipeExtractionProvider(Protocol):
    async def extract(self, sources: list[ExtractionSource], *, language: str, tags: str) -> ExtractionResult:
        raise NotImplementedError
