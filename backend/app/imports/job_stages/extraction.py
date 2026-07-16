from datetime import datetime, timezone

import anyio

from app.ai.provider import RecipeExtractionProvider
from app.ai.schemas import ExtractionResult
from app.imports.error_codes import (
    ExtractorUnavailableError,
    ImportExtractionErrorCode,
    InvalidExtractionResult,
    NotARecipeError,
    ResultParseError,
)
from app.imports.job_context import ImportJobContext
from app.imports.job_stages.extraction_sources import ExtractionContext
from app.imports.logging import log_extraction_finished, log_extraction_started


def extract(
    job: ImportJobContext,
    context: ExtractionContext,
    provider_name: str,
    provider: RecipeExtractionProvider,
) -> ExtractionResult:
    started_at = datetime.now(timezone.utc)
    source_count = len(context.extraction_sources)

    async def extract_recipe():
        return await provider.extract(
            context.extraction_sources,
            language=context.language,
            tags=", ".join(context.tag_names),
        )

    log_extraction_started(job, provider_name, source_count=source_count)

    try:
        result: ExtractionResult = anyio.run(extract_recipe)
    except Exception as error:
        raise ExtractorUnavailableError(original_error=str(error)) from error

    quality_payload = {}
    if result.recipe is not None:
        quality = result.recipe.quality
        quality_payload = {
            "confidence": quality.confidence,
            "has_conflicts": quality.has_conflicts,
            "has_ignored": quality.has_ignored,
            "primary_source_refs": quality.primary_source_refs,
            "ignored_source_refs": quality.ignored_source_refs,
        }
    log_extraction_finished(job, started_at, **quality_payload)
    return result


def validate_extraction_result(
    result: ExtractionResult,
) -> None:
    if result.recipe and not result.not_a_recipe:
        return None
    if result.error_code == ImportExtractionErrorCode.RESULT_PARSE_FAILED:
        raise ResultParseError(provider_message=result.error_message)
    if result.error_code == ImportExtractionErrorCode.INVALID_EXTRACTION_RESULT:
        raise InvalidExtractionResult(provider_message=result.error_message)
    if result.error_code == ImportExtractionErrorCode.EXTRACTOR_UNAVAILABLE:
        raise ExtractorUnavailableError(provider_message=result.error_message)
    raise NotARecipeError(provider_message=result.error_message)
