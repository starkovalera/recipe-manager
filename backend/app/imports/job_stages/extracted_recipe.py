from app.ai.schemas import ExtractedRecipe, ExtractionQuality, ExtractionSource, extraction_source_id
from app.imports.config import ImportConfig
from app.imports.error_codes import NotARecipeError, RecipeTooLongError
from app.models import ImportJob, SourceType
from app.services.recipe_limits import find_recipe_size_violation


def validate_extracted_recipe(
    recipe_result: ExtractedRecipe,
    import_config: ImportConfig,
) -> ExtractedRecipe:
    size_violation = find_recipe_size_violation(recipe_result.ingredients, recipe_result.instructions, import_config)
    if size_violation is not None:
        raise RecipeTooLongError(
            reason=size_violation.reason,
            actual=size_violation.actual,
            limit=size_violation.limit,
        )
    if recipe_result.quality.confidence <= import_config.import_min_confidence:
        raise NotARecipeError(
            message="Import extraction failed. The extracted recipe confidence is too low.",
            confidence=recipe_result.quality.confidence,
        )
    return recipe_result


def _restore_canonical_source_refs(quality: ExtractionQuality, sources: list[ExtractionSource]) -> ExtractionQuality:
    """Restore canonical references."""
    aliases: dict[str, str] = {}
    for source in sources:
        canonical = extraction_source_id(source)
        aliases[canonical] = canonical
        aliases[str(source.position)] = canonical
        if source.type == "IMAGE" and source.source_ref:
            aliases[source.source_ref] = canonical
            aliases[f"image:{source.source_ref}"] = canonical
        elif source.type == "URL" and source.url:
            aliases[source.url] = canonical

    def _normalize(source_ref: str) -> str:
        value = source_ref.strip()
        if value.startswith("sourceId="):
            value = value.removeprefix("sourceId=").strip()
        return aliases.get(value, value)

    quality.primary_source_refs = [_normalize(source_ref) for source_ref in quality.primary_source_refs]
    quality.ignored_source_refs = [_normalize(source_ref) for source_ref in quality.ignored_source_refs]
    return quality


def _is_single_url_import(job: ImportJob) -> bool:
    return len(job.sources) == 1 and job.sources[0].type == SourceType.URL


def _normalize_quality_flags(extracted_recipe: ExtractedRecipe, job: ImportJob) -> None:
    if _is_single_url_import(job):
        extracted_recipe.quality.has_conflicts = False
        extracted_recipe.quality.has_ignored = False


def normalize_extracted_recipe(extracted_recipe: ExtractedRecipe, sources: list[ExtractionSource], job: ImportJob) -> ExtractedRecipe:
    _restore_canonical_source_refs(extracted_recipe.quality, sources)
    _normalize_quality_flags(extracted_recipe, job)
    return extracted_recipe
