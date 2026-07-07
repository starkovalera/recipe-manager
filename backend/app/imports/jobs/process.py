import logging
from datetime import datetime, timezone

import anyio
from sqlalchemy.orm import Session

from app.ai.schemas import ExtractionResult, ExtractionSource
from app.core.config import get_settings
from app.core.errors import ApiError, ImportNotFoundError
from app.core.logging import BoundLogger, bind_logger
from app.embeddings.service import enqueue_recipe_embedding_with_event, prepare_recipe_embedding
from app.imports.config import ImportConfig
from app.imports.constants import (
    IMPORT_LOG_COMPONENT,
    TERMINAL_IMPORT_STATUSES,
)
from app.imports.cover_generation import CoverGenerationContext, generate_cover_image
from app.imports.error_codes import (
    ExtractorUnavailableError,
    ImportExtractionError,
    ImportExtractionErrorCode,
    ImportProcessingError,
    InvalidExtractionResult,
    NotARecipeError,
    ResultParseError,
)
from app.imports.events import record_job_event
from app.imports.job_stages.extraction_sources import build_extraction_context
from app.imports.job_stages.raw_recipe import build_raw_recipe
from app.imports.job_stages.raw_sources import build_raw_sources
from app.imports.job_status import fail_import_job
from app.imports.lifecycle import handle_import_failed, handle_recipe_created
from app.imports.queries import get_import_job as query_import_job
from app.imports.recipe_materialization import (
    apply_extracted_recipe,
    apply_source_statuses,
    create_review_flag_if_needed,
    derive_source_name_from_primary_resources,
    normalize_recipe_result,
)
from app.imports.runtime import get_recipe_extraction_provider, get_url_content_service, get_video_processor
from app.models import (
    ImportJob,
    ImportJobErrorCode,
    ImportJobStatus,
)
from app.services.search_text import refresh_recipe_search_text
from app.storage.base import StorageService
from app.storage.local import LocalStorageService

logger = logging.getLogger(IMPORT_LOG_COMPONENT)


def _start_import_job(session: Session, job: ImportJob, log: BoundLogger) -> None:
    job.status = ImportJobStatus.RUNNING
    job.started_at = datetime.now(timezone.utc)
    record_job_event(job, "worker_started", {"status": job.status.value})
    session.commit()
    log.info(f"{IMPORT_LOG_COMPONENT} Import job processing started")

def _fail_import_and_commit(
    session: Session,
    job: ImportJob,
    storage: StorageService,
    saved_storage_keys: list[str],
    error_code: ImportJobErrorCode,
    message: str | None,
    log: BoundLogger | None = None,
    cleanup_storage: bool = True,
    detail_payload: dict | None = None,
    **log_fields,
) -> None:
    fail_import_job(job, storage, saved_storage_keys, error_code, message, cleanup_storage=cleanup_storage)
    handle_import_failed(session, job, payload=detail_payload)
    session.commit()
    bound_log = log or bind_logger(logger, component=IMPORT_LOG_COMPONENT, owner_id=job.owner_id, import_job_id=job.id)
    bound_log.info(
        f"{IMPORT_LOG_COMPONENT} Import job failed",
        error_code=job.error_code.value if job.error_code else None,
        error_message=job.error_message,
        **log_fields,
    )


def _extract_recipe_with_ai(
    job: ImportJob,
    ready_sources: list[ExtractionSource],
    ai_language: str,
    ai_tags: str,
    log: BoundLogger,
) -> ExtractionResult:
    started_at = datetime.now(timezone.utc)
    provider_name, provider = get_recipe_extraction_provider()

    async def extract_recipe():
        return await provider.extract(ready_sources, language=ai_language, tags=ai_tags)

    log.info(f"{IMPORT_LOG_COMPONENT} AI provider selected", provider=provider_name)
    record_job_event(job, "ai_called", {"provider": provider_name, "sourceCount": len(ready_sources)})
    try:
        result = anyio.run(extract_recipe)
    except Exception as error:
        raise ExtractorUnavailableError(exception=repr(error)) from error
    record_job_event(job, "ai_succeeded", {"notARecipe": result.not_a_recipe})
    log.info(
        f"{IMPORT_LOG_COMPONENT} Import step timing",
        step="ai_extraction",
        duration_ms=int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000),
    )
    return result


def _extraction_error_from_provider_result(result) -> ImportExtractionError:
    if result.error_code == ImportExtractionErrorCode.RESULT_PARSE_FAILED.value:
        return ResultParseError(provider_message=result.error_message)
    if result.error_code == ImportExtractionErrorCode.INVALID_EXTRACTION_RESULT.value:
        return InvalidExtractionResult(provider_message=result.error_message)
    if result.error_code == ImportExtractionErrorCode.EXTRACTOR_UNAVAILABLE.value:
        return ExtractorUnavailableError(provider_message=result.error_message)
    return NotARecipeError(provider_message=result.error_message)


def _fail_extraction_and_commit(
    session: Session,
    job: ImportJob,
    storage: StorageService,
    saved_storage_keys: list[str],
    error: ImportExtractionError,
    log: BoundLogger,
    **log_fields,
) -> None:
    _fail_import_and_commit(
        session,
        job,
        storage,
        saved_storage_keys,
        ImportJobErrorCode.IMPORT_EXTRACTION_FAILED,
        error.code_value(),
        log=log,
        cleanup_storage=True,
        detail_payload={
            "stage": "extraction",
            "detailCode": error.code_value(),
            **error.extra,
        },
        **log_fields,
    )


def _fail_processing_and_commit(
    session: Session,
    job: ImportJob,
    storage: StorageService,
    saved_storage_keys: list[str],
    error: ImportProcessingError | Exception,
    log: BoundLogger,
) -> None:
    if isinstance(error, ImportProcessingError):
        message = error.code_value()
        detail_payload = {
            "stage": "processing",
            "detailCode": error.code_value(),
            **error.extra,
        }
    else:
        message = None
        detail_payload = {"stage": "processing", "diagnosticMessage": repr(error)}
    _fail_import_and_commit(
        session,
        job,
        storage,
        saved_storage_keys,
        ImportJobErrorCode.IMPORT_PROCESSING_FAILED,
        message,
        log=log,
        cleanup_storage=False,
        detail_payload=detail_payload,
    )


def process_import_job(session: Session, job_id: str) -> None:
    job: ImportJob | None = session.get(ImportJob, job_id)
    if job is None or job.status in TERMINAL_IMPORT_STATUSES:
        logger.info(f"{IMPORT_LOG_COMPONENT} Import job id={job_id} is not found or can't be started.")
        return

    log = bind_logger(logger, component=IMPORT_LOG_COMPONENT, job=job.to_dict())

    _start_import_job(session, job, log)

    storage = LocalStorageService(get_settings().upload_dir)
    saved_storage_keys = [source.image_storage_key for source in job.sources if source.image_storage_key]

    import_config = ImportConfig.from_settings(get_settings())

    try:
        raw_sources, imported_author_name = build_raw_sources(
            job,
            storage,
            saved_storage_keys,
            get_url_content_service(),
            get_video_processor(),
            import_config,
        )
        record_job_event(job, "source_downloaded", {"sourceCount": len(raw_sources)})

        recipe, recipe_resources, content_recipe_resources = build_raw_recipe(raw_sources, job.owner_id, imported_author_name)
        extraction_context = build_extraction_context(content_recipe_resources, job, session, storage)
    except Exception as error:
        log.error(f"{IMPORT_LOG_COMPONENT} Import processing failed", error=repr(error))
        _fail_processing_and_commit(session, job, storage, saved_storage_keys, error, log)
        return

    log = bind_logger(
        logger,
        component=IMPORT_LOG_COMPONENT,
        owner_id=job.owner_id,
        import_job_id=job.id,
        source_count=len(extraction_context.extraction_sources),
    )
    try:
        result = _extract_recipe_with_ai(
            job,
            extraction_context.extraction_sources,
            extraction_context.language,
            ", ".join(tag.name for tag in extraction_context.tags),
            log,
        )
    except ImportExtractionError as error:
        log.error(
            f"{IMPORT_LOG_COMPONENT} AI extraction provider threw",
            error=str(error),
        )
        _fail_extraction_and_commit(session, job, storage, saved_storage_keys, error, log)
        return
    if result.not_a_recipe or result.recipe is None:
        _fail_extraction_and_commit(session, job, storage, saved_storage_keys, _extraction_error_from_provider_result(result), log)
        return

    recipe_result = result.recipe
    try:
        recipe_result, status_quality = normalize_recipe_result(job, recipe_result, extraction_context.extraction_sources)
    except ImportExtractionError as error:
        _fail_extraction_and_commit(session, job, storage, saved_storage_keys, error, log)
        return
    except ApiError as error:
        _fail_processing_and_commit(session, job, storage, saved_storage_keys, error, log)
        return
    if recipe_result.quality.confidence <= get_settings().import_min_confidence:
        _fail_extraction_and_commit(
            session,
            job,
            storage,
            saved_storage_keys,
            NotARecipeError(reason="The extracted recipe confidence is too low."),
            log,
            confidence=recipe_result.quality.confidence,
        )
        return
    try:
        log.info(
            f"{IMPORT_LOG_COMPONENT} AI extraction quality",
            confidence=recipe_result.quality.confidence,
            has_conflicts=recipe_result.quality.has_conflicts,
            has_ignored=recipe_result.quality.has_ignored,
            primary_source_refs=recipe_result.quality.primary_source_refs,
            ignored_source_refs=recipe_result.quality.ignored_source_refs,
        )
        apply_extracted_recipe(
            recipe,
            recipe_result,
            active_tags=extraction_context.tags,
            imported_author_name=imported_author_name,
            owner_id=job.owner_id,
            import_job_id=job.id,
        )
        cover_image = generate_cover_image(
            job,
            recipe,
            recipe_result,
            CoverGenerationContext(
                storage=storage,
                saved_storage_keys=saved_storage_keys,
                final_resources=content_recipe_resources,
                ai_id_by_resource=extraction_context.extraction_id_by_resource,
            ),
        )
        has_ignored_primary = apply_source_statuses(recipe_resources, content_recipe_resources, status_quality, extraction_context.extraction_id_by_resource)
        recipe.source_name = derive_source_name_from_primary_resources(recipe_resources)
        refresh_recipe_search_text(recipe)
        has_review_flag = create_review_flag_if_needed(job, recipe, recipe_result, has_ignored_primary)
        session.add(recipe)
        session.flush()
        if cover_image is not None:
            recipe.cover_image_id = cover_image.id
        embedding, should_enqueue_embedding = prepare_recipe_embedding(recipe)
        job.created_recipe_id = recipe.id
        job.status = ImportJobStatus.SUCCEEDED_WITH_FLAGS if has_review_flag else ImportJobStatus.SUCCEEDED
        job.finished_at = datetime.now(timezone.utc)
        handle_recipe_created(session, job, recipe_id=recipe.id, status=job.status)
        session.commit()
        if should_enqueue_embedding:
            enqueue_recipe_embedding_with_event(session, embedding=embedding, owner_id=recipe.owner_id)
            session.commit()
    except Exception as error:
        session.rollback()
        job = session.get(ImportJob, job_id)
        if job is not None and job.status not in TERMINAL_IMPORT_STATUSES:
            _fail_processing_and_commit(session, job, storage, saved_storage_keys, error, log)
        return
    log.info(
        f"{IMPORT_LOG_COMPONENT} Import job succeeded",
        recipe_id=recipe.id,
    )


def get_import_job(session: Session, job_id: str, owner_id: str) -> ImportJob:
    job = query_import_job(session, job_id, owner_id)
    if job is None:
        raise ImportNotFoundError()
    return job
