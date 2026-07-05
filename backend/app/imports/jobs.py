import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import anyio
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.ai.schemas import ReadySource
from app.core.config import get_settings
from app.core.errors import (
    ActiveImportExistsError,
    ApiError,
    FileTooLargeError,
    ImportNotFoundError,
    InvalidFileTypeError,
    NoImportSourcesError,
    RecipeTooLongError,
    TextTooLongError,
    TooManyFilesError,
)
from app.core.logging import BoundLogger, bind_logger
from app.embeddings.service import enqueue_recipe_embedding_with_event, prepare_recipe_embedding
from app.imports.constants import IMPORT_LOG_COMPONENT, IMPORT_LOG_PREFIX
from app.imports.cover_generation import CoverGenerationContext, generate_cover_image
from app.imports.error_codes import (
    ImportCreationError,
    ImportCreationErrorCode,
    ImportExtractionError,
    ImportExtractionErrorCode,
    ImportProcessingError,
)
from app.imports.events import record_job_event
from app.imports.job_status import fail_import_job
from app.imports.lifecycle import handle_import_failed, handle_import_started, handle_recipe_created
from app.imports.queries import (
    count_import_jobs_by_statuses,
    get_import_job as query_import_job,
    get_import_job_by_dedupe_key,
)
from app.imports.recipe_builder import build_ready_sources, build_recipe_from_drafts
from app.imports.recipe_materialization import (
    apply_extracted_recipe,
    apply_source_statuses,
    create_review_flag_if_needed,
    derive_source_name_from_primary_resources,
    normalize_recipe_result,
)
from app.imports.runtime import get_recipe_extraction_provider, get_url_content_loader_registry, get_video_processor
from app.imports.source_drafts import build_source_drafts_for_job
from app.media.images import validate_image_upload
from app.models import (
    ImportJob,
    ImportJobErrorCode,
    ImportJobSource,
    ImportJobStatus,
    ImportSourceStatus,
    Recipe,
    RecipeResource,
    SourceType,
    Tag,
)
from app.services.search_text import refresh_recipe_search_text
from app.storage.local import LocalStorageService
from app.tags.queries import list_active_tags

logger = logging.getLogger(IMPORT_LOG_COMPONENT)


SUPPORTED_UPLOAD_TYPES = {"image/jpeg", "image/png", "image/webp"}
ACTIVE_IMPORT_STATUSES = {ImportJobStatus.QUEUED, ImportJobStatus.RUNNING}
TERMINAL_IMPORT_STATUSES = {
    ImportJobStatus.SUCCEEDED,
    ImportJobStatus.SUCCEEDED_WITH_FLAGS,
    ImportJobStatus.FAILED,
    ImportJobStatus.CANCELLED,
}


@dataclass
class ImportJobCreationResult:
    job: ImportJob
    was_created: bool


@dataclass
class ImportProcessingContext:
    storage: LocalStorageService
    saved_storage_keys: list[str]
    imported_author_name: str | None
    recipe: Recipe
    recipe_resources: list[RecipeResource]
    final_resources: list[RecipeResource]
    ai_id_by_resource: dict[RecipeResource, str]
    ready_sources: list[ReadySource]
    active_tags: list[Tag]
    ai_language: str
    ai_tags: str


def _validate_import_request(text: str | None, url: str | None, files: list[UploadFile]) -> tuple[str | None, str | None]:
    settings = get_settings()
    normalized_text = text.strip() if text else None
    normalized_url = url.strip() if url else None
    if normalized_text and len(normalized_text) > settings.max_import_text_chars:
        raise TextTooLongError(max_length=settings.max_import_text_chars)
    if len(files) > settings.max_import_images:
        raise TooManyFilesError(max_files=settings.max_import_images)
    for upload in files:
        if upload.content_type not in SUPPORTED_UPLOAD_TYPES:
            raise InvalidFileTypeError(content_type=upload.content_type)
    if not normalized_text and not normalized_url and not files:
        raise NoImportSourcesError()
    return normalized_text, normalized_url


def _create_upload_source(upload: UploadFile, position: int, storage: LocalStorageService) -> ImportJobSource:
    content = upload.file.read()
    if len(content) > get_settings().max_upload_bytes:
        raise FileTooLargeError(max_size_bytes=get_settings().max_upload_bytes)
    try:
        validated = validate_image_upload(content, upload.content_type or "", upload.filename or "upload")
    except ValueError as error:
        raise InvalidFileTypeError(message=str(error), content_type=upload.content_type, filename=upload.filename) from error
    saved = storage.save(validated.content, validated.original_name, validated.mime_type)
    return ImportJobSource(
        type=SourceType.IMAGE,
        status=ImportSourceStatus.READY,
        image_storage_key=saved.storage_key,
        original_name=saved.original_name,
        mime_type=saved.mime_type,
        size_bytes=saved.size_bytes,
        position=position,
    )


def create_import_job(
    session: Session,
    owner_id: str,
    client_id: str,
    client_import_id: str,
    text: str | None,
    url: str | None,
    files: list[UploadFile] | None = None,
    idempotency_key: str | None = None,
) -> ImportJobCreationResult:
    files = files or []
    normalized_text, normalized_url = _validate_import_request(text, url, files)
    normalized_idempotency_key = idempotency_key.strip()[:128] if idempotency_key else ""
    dedupe_key = normalized_idempotency_key or client_import_id

    existing = get_import_job_by_dedupe_key(session, owner_id, dedupe_key)
    if existing is not None:
        return ImportJobCreationResult(job=existing, was_created=False)
    if count_import_jobs_by_statuses(session, owner_id, ACTIVE_IMPORT_STATUSES) >= get_settings().max_parallel_imports_per_client:
        raise ActiveImportExistsError(max_active_imports=get_settings().max_parallel_imports_per_client)

    job = ImportJob(
        owner_id=owner_id,
        client_id=client_id,
        client_import_id=client_import_id,
        dedupe_key=dedupe_key,
        status=ImportJobStatus.QUEUED,
    )
    position = 0
    storage = LocalStorageService(get_settings().upload_dir)
    session.add(job)
    session.flush()
    saved_storage_keys: list[str] = []
    try:
        for upload in files:
            try:
                source = _create_upload_source(upload, position, storage)
            except Exception as error:
                raise ImportCreationError(
                    ImportCreationErrorCode.RESOURCE_UPLOAD_FAILED,
                    diagnostic_message=repr(error),
                    payload={
                        "resourcePosition": position,
                        "resourceType": SourceType.IMAGE.value,
                        "originalName": upload.filename,
                        "contentType": upload.content_type,
                    },
                ) from error
            job.sources.append(source)
            if source.image_storage_key:
                saved_storage_keys.append(source.image_storage_key)
            position += 1
        if normalized_text:
            job.sources.append(ImportJobSource(type=SourceType.TEXT, status=ImportSourceStatus.READY, text=normalized_text, position=position))
            position += 1
        if normalized_url:
            job.sources.append(ImportJobSource(type=SourceType.URL, status=ImportSourceStatus.READY, url=normalized_url, position=position))
        handle_import_started(session, job, client_import_id=client_import_id, dedupe_key=dedupe_key)
        session.commit()
    except ImportCreationError as error:
        _fail_import_and_commit(
            session,
            job,
            storage,
            saved_storage_keys,
            ImportJobErrorCode.IMPORT_CREATION_FAILED,
            error.detail_code.value if error.detail_code else None,
            detail_payload={"stage": "creation", "detailCode": error.detail_code.value if error.detail_code else None, **error.payload},
            diagnosticMessage=error.diagnostic_message,
        )
    except Exception as error:
        _fail_import_and_commit(
            session,
            job,
            storage,
            saved_storage_keys,
            ImportJobErrorCode.IMPORT_CREATION_FAILED,
            None,
            detail_payload={"stage": "creation"},
            diagnosticMessage=repr(error),
        )
    session.refresh(job)
    bind_logger(
        logger,
        component=IMPORT_LOG_COMPONENT,
        ownerId=owner_id,
        importJobId=job.id,
        clientId=client_id,
        clientImportId=client_import_id,
        dedupeKey=dedupe_key,
        sourceCount=len(job.sources),
        hasText=normalized_text is not None,
        hasUrl=normalized_url is not None,
        attachmentCount=len(files),
    ).info(f"{IMPORT_LOG_PREFIX} Import job created")
    return ImportJobCreationResult(job=job, was_created=True)


def _start_import_job(session: Session, job: ImportJob, log: BoundLogger) -> None:
    job.status = ImportJobStatus.RUNNING
    job.started_at = datetime.now(timezone.utc)
    record_job_event(job, "worker_started", {"status": job.status.value})
    session.commit()
    log.info(f"{IMPORT_LOG_PREFIX} Import job processing started")


def _build_import_processing_context(
    session: Session,
    job: ImportJob,
    storage: LocalStorageService,
    saved_storage_keys: list[str],
) -> ImportProcessingContext:
    source_drafts, imported_author_name = build_source_drafts_for_job(
        job,
        storage,
        saved_storage_keys,
        get_url_content_loader_registry(),
        get_video_processor(),
        get_settings(),
        logger,
    )
    record_job_event(job, "source_downloaded", {"sourceCount": len(source_drafts)})

    built_sources = build_recipe_from_drafts(job.owner_id, source_drafts)
    active_tags = list_active_tags(session, job.owner_id)
    ai_language = job.owner.settings.recipe_language if job.owner and job.owner.settings else get_settings().recipe_language
    ai_tags = ", ".join(tag.name for tag in active_tags)
    return ImportProcessingContext(
        storage=storage,
        saved_storage_keys=saved_storage_keys,
        imported_author_name=imported_author_name,
        recipe=built_sources.recipe,
        recipe_resources=built_sources.recipe_resources,
        final_resources=built_sources.final_resources,
        ai_id_by_resource=built_sources.ai_id_by_resource,
        ready_sources=build_ready_sources(built_sources.final_resources, built_sources.ai_id_by_resource, storage),
        active_tags=active_tags,
        ai_language=ai_language,
        ai_tags=ai_tags,
    )


def _fail_import_and_commit(
    session: Session,
    job: ImportJob,
    storage: LocalStorageService,
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
    bound_log = log or bind_logger(logger, component=IMPORT_LOG_COMPONENT, ownerId=job.owner_id, importJobId=job.id)
    bound_log.info(
        f"{IMPORT_LOG_PREFIX} Import job failed",
        errorCode=job.error_code.value if job.error_code else None,
        errorMessage=job.error_message,
        **log_fields,
    )


def _extract_recipe_with_ai(job: ImportJob, ready_sources: list[ReadySource], ai_language: str, ai_tags: str, log: BoundLogger):
    started_at = datetime.now(timezone.utc)
    provider_name, provider = get_recipe_extraction_provider()

    async def extract_recipe():
        return await provider.extract(ready_sources, language=ai_language, tags=ai_tags)

    log.info(f"{IMPORT_LOG_PREFIX} AI provider selected", provider=provider_name)
    record_job_event(job, "ai_called", {"provider": provider_name, "sourceCount": len(ready_sources)})
    try:
        result = anyio.run(extract_recipe)
    except Exception as error:
        raise ImportExtractionError(
            ImportExtractionErrorCode.AI_UNAVAILABLE,
            diagnostic_message=repr(error),
        ) from error
    record_job_event(job, "ai_succeeded", {"notARecipe": result.not_a_recipe})
    log.info(
        f"{IMPORT_LOG_PREFIX} Import step timing",
        step="ai_extraction",
        durationMs=int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000),
    )
    return result


def _extraction_error_from_provider_result(result) -> ImportExtractionError:
    if result.error_code == ImportExtractionErrorCode.AI_PARSE_FAILED.value:
        return ImportExtractionError(ImportExtractionErrorCode.AI_PARSE_FAILED, diagnostic_message=result.error_message)
    if result.error_code == ImportExtractionErrorCode.INVALID_EXTRACTION_RESULT.value:
        return ImportExtractionError(ImportExtractionErrorCode.INVALID_EXTRACTION_RESULT, diagnostic_message=result.error_message)
    if result.error_code == ImportExtractionErrorCode.AI_UNAVAILABLE.value:
        return ImportExtractionError(ImportExtractionErrorCode.AI_UNAVAILABLE, diagnostic_message=result.error_message)
    return ImportExtractionError(ImportExtractionErrorCode.NOT_A_RECIPE, diagnostic_message=result.error_message)


def _fail_extraction_and_commit(
    session: Session,
    job: ImportJob,
    storage: LocalStorageService,
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
        error.detail_code.value,
        log=log,
        cleanup_storage=True,
        detail_payload={
            "stage": "extraction",
            "detailCode": error.detail_code.value,
            "diagnosticMessage": error.diagnostic_message,
            **error.payload,
        },
        **log_fields,
    )


def _fail_processing_and_commit(
    session: Session,
    job: ImportJob,
    storage: LocalStorageService,
    saved_storage_keys: list[str],
    error: ImportProcessingError | Exception,
    log: BoundLogger,
) -> None:
    if isinstance(error, ImportProcessingError):
        message = error.detail_code.value if error.detail_code else None
        detail_payload = {
            "stage": "processing",
            "detailCode": error.detail_code.value if error.detail_code else None,
            "diagnosticMessage": error.diagnostic_message,
            **error.payload,
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
    job = session.get(ImportJob, job_id)
    if job is None or job.status in TERMINAL_IMPORT_STATUSES:
        return
    log = bind_logger(logger, component=IMPORT_LOG_COMPONENT, ownerId=job.owner_id, importJobId=job.id)
    _start_import_job(session, job, log)

    storage = LocalStorageService(get_settings().upload_dir)
    saved_storage_keys = [source.image_storage_key for source in job.sources if source.image_storage_key]
    try:
        context = _build_import_processing_context(session, job, storage, saved_storage_keys)
    except Exception as error:
        log.error(f"{IMPORT_LOG_PREFIX} Import processing failed", error=repr(error))
        _fail_processing_and_commit(session, job, storage, saved_storage_keys, error, log)
        return
    recipe = context.recipe
    recipe_resources = context.recipe_resources
    final_resources = context.final_resources
    ai_id_by_resource = context.ai_id_by_resource
    ready_sources = context.ready_sources
    log = bind_logger(logger, component=IMPORT_LOG_COMPONENT, ownerId=job.owner_id, importJobId=job.id, sourceCount=len(ready_sources))
    try:
        result = _extract_recipe_with_ai(job, ready_sources, context.ai_language, context.ai_tags, log)
    except ImportExtractionError as error:
        log.error(
            f"{IMPORT_LOG_PREFIX} AI extraction provider threw",
            error=error.diagnostic_message,
        )
        _fail_extraction_and_commit(session, job, storage, saved_storage_keys, error, log)
        return
    if result.not_a_recipe or result.recipe is None:
        _fail_extraction_and_commit(session, job, storage, saved_storage_keys, _extraction_error_from_provider_result(result), log)
        return

    recipe_result = result.recipe
    try:
        recipe_result, status_quality = normalize_recipe_result(job, recipe_result, ready_sources)
    except ApiError as error:
        if isinstance(error, RecipeTooLongError):
            _fail_extraction_and_commit(
                session,
                job,
                storage,
                saved_storage_keys,
                ImportExtractionError(ImportExtractionErrorCode.RECIPE_TOO_LONG, diagnostic_message=error.message),
                log,
            )
            return
        _fail_processing_and_commit(session, job, storage, saved_storage_keys, error, log)
        return
    if recipe_result.quality.confidence <= get_settings().import_min_confidence:
        _fail_extraction_and_commit(
            session,
            job,
            storage,
            saved_storage_keys,
            ImportExtractionError(
                ImportExtractionErrorCode.NOT_A_RECIPE,
                diagnostic_message="The extracted recipe confidence is too low.",
            ),
            log,
            confidence=recipe_result.quality.confidence,
        )
        return
    try:
        log.info(
            f"{IMPORT_LOG_PREFIX} AI extraction quality",
            confidence=recipe_result.quality.confidence,
            hasConflicts=recipe_result.quality.hasConflicts,
            hasIgnored=recipe_result.quality.hasIgnored,
            primarySourceRefs=recipe_result.quality.primarySourceRefs,
            ignoredSourceRefs=recipe_result.quality.ignoredSourceRefs,
        )
        apply_extracted_recipe(
            recipe,
            recipe_result,
            active_tags=context.active_tags,
            imported_author_name=context.imported_author_name,
            owner_id=job.owner_id,
            import_job_id=job.id,
        )
        cover_image = generate_cover_image(
            job,
            recipe,
            recipe_result,
            CoverGenerationContext(
                storage=context.storage,
                saved_storage_keys=context.saved_storage_keys,
                final_resources=context.final_resources,
                ai_id_by_resource=context.ai_id_by_resource,
            ),
        )
        has_ignored_primary = apply_source_statuses(recipe_resources, final_resources, status_quality, ai_id_by_resource)
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
        f"{IMPORT_LOG_PREFIX} Import job succeeded",
        recipeId=recipe.id,
    )


def get_import_job(session: Session, job_id: str, owner_id: str) -> ImportJob:
    job = query_import_job(session, job_id, owner_id)
    if job is None:
        raise ImportNotFoundError()
    return job
