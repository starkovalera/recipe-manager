import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai.schemas import ExtractedRecipe
from app.core.config import get_settings
from app.core.errors import ImportNotFoundError
from app.core.logging import bind_logger
from app.db.session import db_session
from app.embeddings.queries import get_recipe_embedding
from app.embeddings.service import enqueue_recipe_embedding_with_event, prepare_recipe_embedding
from app.imports.config import ImportConfig
from app.imports.constants import (
    IMPORT_LOG_COMPONENT,
    TERMINAL_IMPORT_STATUSES,
)
from app.imports.cover_generation import CoverGenerationContext, generate_cover_image
from app.imports.events import build_job_event
from app.imports.job_context import ImportJobContext
from app.imports.job_stages.extracted_recipe import normalize_extracted_recipe, validate_extracted_recipe
from app.imports.job_stages.extraction import extract, validate_extraction_result
from app.imports.job_stages.extraction_sources import build_extraction_context
from app.imports.job_stages.failure import process_import_failure
from app.imports.job_stages.raw_recipe import build_raw_recipe
from app.imports.job_stages.raw_sources import build_raw_sources
from app.imports.job_stages.recipe_building import build_recipe
from app.imports.logging import log_import_started, log_recipe_created
from app.imports.queries import get_import_job as query_import_job
from app.imports.recipe_materialization import (
    apply_source_statuses,
    create_review_flag_if_needed,
    derive_source_name_from_primary_resources,
)
from app.imports.runtime import get_recipe_extraction_provider, get_url_content_service, get_video_processor
from app.models import (
    ImportEventType,
    ImportJob,
    ImportJobStatus,
)
from app.notifications.notification_data import (
    ImportSucceededNotification,
    ImportSucceededWithFlagsNotification,
    build_notification,
)
from app.services.search_text import refresh_recipe_search_text
from app.storage.local import LocalStorageService
from app.tags.queries import list_active_tags

logger = bind_logger(logging.getLogger(__name__), component=IMPORT_LOG_COMPONENT)


@dataclass(frozen=True)
class ImportResult:
    job: ImportJobContext
    recipe_id: str
    enqueue_embedding: bool


def start_import_job(session: Session, job_id: str) -> ImportJob | None:
    job: ImportJob | None = session.get(ImportJob, job_id)
    if job is None or job.status in TERMINAL_IMPORT_STATUSES:
        return None

    job.set_running()
    build_job_event(session, import_job_id=job.id, event_type=ImportEventType.IMPORT_STARTED, status=job.status.value)
    session.flush()
    session.refresh(job)
    return job


def enqueue_recipe_embedding_for_import(session: Session, *, recipe_id: str, owner_id: str) -> None:
    embedding = get_recipe_embedding(session, recipe_id)
    if embedding is not None:
        enqueue_recipe_embedding_with_event(session, embedding=embedding, owner_id=owner_id)


def persist_import_success(
    *,
    session: Session,
    job_id: str,
    job_context: ImportJobContext,
    recipe,
    recipe_resources,
    content_recipe_resources,
    extraction_context,
    extracted_recipe: ExtractedRecipe,
    storage,
    saved_storage_keys: list[str],
) -> ImportResult:
    job: ImportJob | None = session.get(ImportJob, job_id)
    if job is None:
        raise RuntimeError(f"Import job {job_id} not found while persisting import success.")

    build_recipe(recipe, extracted_recipe, list_active_tags(session, job_context.owner_id), job_context)
    cover_image = generate_cover_image(
        job_context,
        recipe,
        extracted_recipe,
        CoverGenerationContext(
            storage=storage,
            saved_storage_keys=saved_storage_keys,
            final_resources=content_recipe_resources,
            ai_id_by_resource=extraction_context.extraction_id_by_resource,
        ),
    )

    has_ignored_primary = apply_source_statuses(
        recipe_resources,
        content_recipe_resources,
        extracted_recipe.quality,
        extraction_context.extraction_id_by_resource,
    )
    recipe.source_name = derive_source_name_from_primary_resources(recipe_resources)
    refresh_recipe_search_text(recipe)
    has_review_flag = create_review_flag_if_needed(job_context, recipe, extracted_recipe, has_ignored_primary)
    session.add(recipe)
    session.flush()
    if cover_image is not None:
        recipe.cover_image_id = cover_image.id
    _embedding, enqueue_embedding = prepare_recipe_embedding(recipe)

    if has_review_flag:
        job_status, notification_cls = ImportJobStatus.SUCCEEDED_WITH_FLAGS, ImportSucceededWithFlagsNotification
    else:
        job_status, notification_cls = ImportJobStatus.SUCCEEDED, ImportSucceededNotification
    job.set_recipe_created(recipe.id, job_status)
    build_job_event(session, import_job_id=job.id, event_type=ImportEventType.RECIPE_CREATED, recipe_id=recipe.id, status=job_status.value)
    build_notification(
        session,
        notification_cls,
        owner_id=job.owner_id,
        entity_id=recipe.id,
    )
    session.flush()
    session.refresh(job)
    return ImportResult(job=ImportJobContext.from_job(job), recipe_id=recipe.id, enqueue_embedding=enqueue_embedding)


def process_import_job(job_id: str) -> None:
    settings = get_settings()
    storage = LocalStorageService(settings.upload_dir)
    import_config = ImportConfig.from_settings(settings)
    saved_storage_keys: list[str] = []

    try:
        with db_session() as session:
            job = start_import_job(session, job_id)
            if job is None:
                logger.info(f"{IMPORT_LOG_COMPONENT} Import job id={job_id} is not found or can't be started.")
                return
            job_context = ImportJobContext.from_job(job)

        saved_storage_keys = job_context.image_storage_keys
        log_import_started(job_context)

        raw_sources, imported_author_name = build_raw_sources(
            job_context,
            storage,
            saved_storage_keys,
            get_url_content_service(),
            get_video_processor(),
            import_config,
        )
        with db_session() as session:
            build_job_event(
                session,
                import_job_id=job_context.id,
                event_type=ImportEventType.RAW_SOURCES_DOWNLOADED,
                source_count=len(raw_sources),
            )

        recipe, recipe_resources, content_recipe_resources = build_raw_recipe(raw_sources, job_context.owner_id, imported_author_name)

        extraction_context = build_extraction_context(content_recipe_resources, job_context, storage)

        provider_name, provider = get_recipe_extraction_provider()
        with db_session() as session:
            build_job_event(
                session,
                import_job_id=job_context.id,
                event_type=ImportEventType.EXTRACTOR_REQUESTED,
                provider=provider_name,
                source_count=len(extraction_context.extraction_sources),
            )
        extraction_result = extract(job_context, extraction_context, provider_name, provider)
        with db_session() as session:
            build_job_event(
                session,
                import_job_id=job_context.id,
                event_type=ImportEventType.EXTRACTOR_SUCCEEDED,
                not_a_recipe=extraction_result.not_a_recipe,
            )
        validate_extraction_result(extraction_result)
        extracted_recipe = normalize_extracted_recipe(
            validate_extracted_recipe(extraction_result.recipe, import_config),
            extraction_context.extraction_sources,
            job_context,
        )

        with db_session() as session:
            import_result = persist_import_success(
                session=session,
                job_id=job_context.id,
                job_context=job_context,
                recipe=recipe,
                recipe_resources=recipe_resources,
                content_recipe_resources=content_recipe_resources,
                extraction_context=extraction_context,
                extracted_recipe=extracted_recipe,
                storage=storage,
                saved_storage_keys=saved_storage_keys,
            )

        log_recipe_created(import_result.job)

        if import_result.enqueue_embedding:
            with db_session() as session:
                enqueue_recipe_embedding_for_import(
                    session,
                    recipe_id=import_result.recipe_id,
                    owner_id=job_context.owner_id,
                )
    except Exception as error:
        process_import_failure(job_id, storage, saved_storage_keys, error, cleanup_storage=True)
        return


def get_import_job(session: Session, job_id: str, owner_id: str, raise_error: bool = True) -> ImportJob | None:
    job = query_import_job(session, job_id, owner_id)
    if job is None and raise_error:
        raise ImportNotFoundError()
    return job
