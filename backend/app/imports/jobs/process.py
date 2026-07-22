import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai.schemas import ExtractedRecipe
from app.core.config import get_settings
from app.core.errors import ImportNotFoundError
from app.core.logging import bind_logger
from app.db.session import db_session
from app.embeddings.planning import prepare_recipe_embedding
from app.imports.config import ImportConfig
from app.imports.constants import IMPORT_LOG_COMPONENT
from app.imports.events import build_job_event
from app.imports.job_context import ImportJobContext
from app.imports.job_stages.cover_generation import PreparedCoverImage, attach_cover_image, prepare_cover_image
from app.imports.job_stages.extracted_recipe import normalize_extracted_recipe, validate_extracted_recipe
from app.imports.job_stages.extraction import extract, validate_extraction_result
from app.imports.job_stages.extraction_sources import ExtractionContext, build_extraction_context
from app.imports.job_stages.failure import process_import_failure
from app.imports.job_stages.flags import set_flags
from app.imports.job_stages.raw_recipe import build_raw_recipe
from app.imports.job_stages.raw_sources import build_raw_sources
from app.imports.job_stages.recipe_building import build_recipe
from app.imports.job_stages.recipe_resource_building import build_recipe_resources
from app.imports.logging import log_import_started, log_recipe_created
from app.imports.outcomes import ImportProcessingDisposition, ImportProcessingResult
from app.imports.queries import (
    get_import_job as query_import_job,
    get_queued_import_job_for_update,
)
from app.imports.runtime import get_recipe_extraction_provider, get_url_content_service, get_video_processor
from app.models import (
    ImportEventType,
    ImportJob,
    ImportJobStatus,
    Recipe,
    RecipeResource,
)
from app.notifications.notification_data import (
    ImportSucceededNotification,
    ImportSucceededWithFlagsNotification,
    build_notification,
)
from app.queueing.outbox import dispatch_outbox_message
from app.services.search_text import refresh_recipe_search_text
from app.storage.runtime import get_storage_service
from app.tags.queries import list_active_tags

logger = bind_logger(logging.getLogger(__name__), component=IMPORT_LOG_COMPONENT)


@dataclass(frozen=True)
class ImportResult:
    job: ImportJobContext
    recipe_id: str
    embedding_outbox_message_id: str | None


def start_import_job(session: Session, job_id: str, import_config: ImportConfig) -> ImportJob | None:
    job = get_queued_import_job_for_update(session, job_id)
    if job is None:
        return None

    job.set_running()
    build_job_event(
        session,
        import_job_id=job.id,
        event_type=ImportEventType.IMPORT_STARTED,
        status=job.status.value,
        attempt_count=job.attempt_count,
        max_attempts=import_config.max_import_attempts,
    )
    session.flush()
    session.refresh(job)
    return job


def save_import(
    *,
    session: Session,
    job_context: ImportJobContext,
    recipe: Recipe,
    recipe_resources: list[RecipeResource],
    content_recipe_resources: list[RecipeResource],
    extraction_context: ExtractionContext,
    extracted_recipe: ExtractedRecipe,
    import_config: ImportConfig,
    prepared_cover: PreparedCoverImage | None,
) -> ImportResult:
    job: ImportJob | None = session.get(ImportJob, job_context.id)
    if job is None:
        raise RuntimeError(f"Import job {job_context.id} not found while persisting import success.")

    build_recipe(recipe, extracted_recipe, list_active_tags(session, job_context.owner_id), job_context)
    attach_cover_image(job_context, recipe, prepared_cover)
    has_ignored_primary_resource = build_recipe_resources(
        recipe,
        recipe_resources,
        content_recipe_resources,
        extraction_context.extraction_id_by_resource,
        extracted_recipe.quality,
    )
    has_flags = set_flags(job_context, recipe, extracted_recipe, has_ignored_primary_resource, import_config)
    if has_flags:
        job_status, notification_cls = ImportJobStatus.SUCCEEDED_WITH_FLAGS, ImportSucceededWithFlagsNotification
    else:
        job_status, notification_cls = ImportJobStatus.SUCCEEDED, ImportSucceededNotification

    refresh_recipe_search_text(recipe)

    session.add(recipe)
    session.flush()

    embedding_plan = prepare_recipe_embedding(session, recipe)

    job.set_recipe_created(recipe.id, job_status)
    build_job_event(
        session,
        import_job_id=job.id,
        event_type=ImportEventType.RECIPE_CREATED,
        recipe_id=recipe.id,
        status=job_status.value,
    )
    build_notification(
        session,
        notification_cls,
        owner_id=job.owner_id,
        entity_id=recipe.id,
    )

    session.flush()
    session.refresh(job)
    return ImportResult(
        job=ImportJobContext.from_job(job),
        recipe_id=recipe.id,
        embedding_outbox_message_id=embedding_plan.outbox_message_id,
    )


def process_import_job(job_id: str) -> ImportProcessingResult:
    settings = get_settings()
    storage = get_storage_service(settings)
    import_config = ImportConfig.from_settings(settings)

    with db_session() as session:
        job = start_import_job(session, job_id, import_config)
        if job is None:
            logger.info(f"{IMPORT_LOG_COMPONENT} Import job id={job_id} is not found or can't be started.")
            return ImportProcessingResult(
                import_job_id=job_id,
                disposition=ImportProcessingDisposition.NOOP,
            )
        job_context = ImportJobContext.from_job(job)

    primary_storage_keys = job_context.primary_storage_keys
    secondary_storage_keys: list[str] = []

    try:
        log_import_started(job_context)

        raw_sources_result = build_raw_sources(
            job_context,
            storage,
            secondary_storage_keys,
            get_url_content_service(),
            get_video_processor(),
            import_config,
        )
        with db_session() as session:
            if raw_sources_result.failed_secondary_resources:
                build_job_event(
                    session,
                    import_job_id=job_context.id,
                    event_type=ImportEventType.IMPORT_SECONDARY_RESOURCE_UPLOAD_FAILED,
                    attempt_count=job_context.attempt_count,
                    max_attempts=import_config.max_import_attempts,
                    resources=[result.to_dict() for result in raw_sources_result.failed_secondary_resources],
                )
            build_job_event(
                session,
                import_job_id=job_context.id,
                event_type=ImportEventType.RAW_SOURCES_DOWNLOADED,
                source_count=len(raw_sources_result.raw_sources),
            )

        recipe, recipe_resources, content_recipe_resources = build_raw_recipe(
            raw_sources_result.raw_sources,
            job_context.owner_id,
            raw_sources_result.imported_author_name,
        )

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
        )

        prepared_cover = prepare_cover_image(
            job_context,
            extracted_recipe,
            content_recipe_resources,
            extraction_context.extraction_id_by_resource,
            storage,
        )
        if prepared_cover is not None:
            secondary_storage_keys.append(prepared_cover.storage_key)

        with db_session() as session:
            import_result = save_import(
                session=session,
                job_context=job_context,
                recipe=recipe,
                recipe_resources=recipe_resources,
                content_recipe_resources=content_recipe_resources,
                extraction_context=extraction_context,
                extracted_recipe=extracted_recipe,
                import_config=import_config,
                prepared_cover=prepared_cover,
            )

        log_recipe_created(import_result.job)

        if import_result.embedding_outbox_message_id is not None:
            dispatch_outbox_message(import_result.embedding_outbox_message_id)
    except Exception as error:
        return process_import_failure(
            job_id,
            storage,
            primary_storage_keys,
            secondary_storage_keys,
            import_config.max_import_attempts,
            error,
            cleanup_storage=True,
        )

    return ImportProcessingResult(
        import_job_id=job_id,
        disposition=ImportProcessingDisposition.SUCCEEDED,
    )


def get_import_job(session: Session, job_id: str, owner_id: str, raise_error: bool = True) -> ImportJob | None:
    job = query_import_job(session, job_id, owner_id)
    if job is None and raise_error:
        raise ImportNotFoundError()
    return job
