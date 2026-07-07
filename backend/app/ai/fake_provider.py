from app.ai.provider import RecipeExtractionProvider
from app.ai.schemas import ExtractedRecipe, ExtractionQuality, ExtractionResult, ExtractionSource, extraction_source_id


class FakeRecipeExtractionProvider(RecipeExtractionProvider):
    async def extract(self, sources: list[ExtractionSource], *, language: str, tags: str) -> ExtractionResult:
        if not sources:
            return ExtractionResult(not_a_recipe=True)
        primary_refs = [extraction_source_id(source) for source in sources]
        return ExtractionResult(
            recipe=ExtractedRecipe(
                title="Imported Recipe",
                ingredients=[{"name": "Ingredient"}],
                instructions=["Cook until done."],
                quality=ExtractionQuality(
                    confidence=0.9,
                    hasConflicts=False,
                    hasIgnored=False,
                    primarySourceRefs=primary_refs,
                    ignoredSourceRefs=[],
                ),
                coverCandidate=None,
            )
        )
