from datetime import datetime, timezone

import anyio

from app.ai.schemas import ExtractionResult
from app.imports.error_codes import (
    ExtractorUnavailableError,
    ImportExtractionErrorCode,
    InvalidExtractionResult,
    NotARecipeError,
    ResultParseError,
)
from app.imports.events import build_job_event
from app.imports.job_stages.extraction_sources import ExtractionContext
from app.imports.logging import log_extraction_finished, log_extraction_started
from app.imports.runtime import get_recipe_extraction_provider
from app.models import ImportEventType, ImportJob


def _extract(
    job: ImportJob,
    context: ExtractionContext,
) -> ExtractionResult:
    started_at = datetime.now(timezone.utc)
    source_count = len(context.extraction_sources)
    provider_name, provider = get_recipe_extraction_provider()

    async def extract_recipe():
        return await provider.extract(
            context.extraction_sources,
            language=context.language,
            tags=", ".join(tag.name for tag in context.tags)
        )

    log_extraction_started(job, provider_name, source_count=source_count)
    build_job_event(job, ImportEventType.EXTRACTOR_REQUESTED, provider=provider_name, source_count=source_count)

    try:
        result: ExtractionResult = anyio.run(extract_recipe)
    except Exception as error:
        raise ExtractorUnavailableError(original_error=str(error)) from error

    build_job_event(job, ImportEventType.EXTRACTOR_SUCCEEDED, not_a_recipe=result.not_a_recipe)
    log_extraction_finished(job, started_at)
    return result


def _validate_extraction_result(
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


def extract(
    job: ImportJob,
    context: ExtractionContext,
) -> ExtractionResult:
    result = _extract(job, context)
    _validate_extraction_result(result)
    return result
