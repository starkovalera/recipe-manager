import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ImportNotFoundError
from app.core.logging import bind_logger
from app.embeddings.service import enqueue_recipe_embedding_with_event, prepare_recipe_embedding
from app.imports.config import ImportConfig
from app.imports.constants import (
    IMPORT_LOG_COMPONENT,
    TERMINAL_IMPORT_STATUSES,
)
from app.imports.cover_generation import CoverGenerationContext, generate_cover_image
from app.imports.events import build_job_event
from app.imports.job_stages.extracted_recipe import normalize_extracted_recipe, validate_extracted_recipe
from app.imports.job_stages.extraction import extract
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
from app.imports.runtime import get_url_content_service, get_video_processor
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

logger = bind_logger(logging.getLogger(__name__), component=IMPORT_LOG_COMPONENT)


def process_import_job(session: Session, job_id: str) -> None:
    job: ImportJob | None = session.get(ImportJob, job_id)
    if job is None or job.status in TERMINAL_IMPORT_STATUSES:
        logger.info(f"{IMPORT_LOG_COMPONENT} Import job id={job_id} is not found or can't be started.")
        return

    # start the job
    job.set_running()
    build_job_event(job, ImportEventType.IMPORT_STARTED, status=job.status.value)
    session.commit()
    session.refresh(job)
    log_import_started(job)

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
        build_job_event(job, ImportEventType.RAW_SOURCES_DOWNLOADED, source_count=len(raw_sources))

        recipe, recipe_resources, content_recipe_resources = build_raw_recipe(raw_sources, job.owner_id, imported_author_name)

        extraction_context = build_extraction_context(content_recipe_resources, job, session, storage)
        extracted_recipe = normalize_extracted_recipe(
            validate_extracted_recipe(extract(job, extraction_context), import_config),
            extraction_context.extraction_sources,
            job,
        )
    except Exception as error:
        process_import_failure(job, session, storage, saved_storage_keys, error, cleanup_storage=True)
        return

    try:
        build_recipe(recipe, extracted_recipe, extraction_context, job)
        cover_image = generate_cover_image(
            job,
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
        has_review_flag = create_review_flag_if_needed(job, recipe, extracted_recipe, has_ignored_primary)
        session.add(recipe)
        session.flush()
        if cover_image is not None:
            recipe.cover_image_id = cover_image.id
        embedding, should_enqueue_embedding = prepare_recipe_embedding(recipe)

        if has_review_flag:
            job_status, notification_cls = ImportJobStatus.SUCCEEDED_WITH_FLAGS, ImportSucceededWithFlagsNotification
        else:
            job_status, notification_cls = ImportJobStatus.SUCCEEDED, ImportSucceededNotification
        job.set_recipe_created(recipe.id, job_status)
        build_job_event(job, ImportEventType.RECIPE_CREATED, recipe_id=recipe.id, status=job_status.value)
        build_notification(
            session,
            notification_cls,
            owner_id=job.owner_id,
            entity_id=recipe.id,
        )
        session.commit()
        session.refresh(job)
        log_recipe_created(job)

        if should_enqueue_embedding:
            enqueue_recipe_embedding_with_event(session, embedding=embedding, owner_id=recipe.owner_id)
            session.commit()
    except Exception as error:
        session.rollback()
        job = session.get(ImportJob, job_id)
        if job is not None and job.status not in TERMINAL_IMPORT_STATUSES:
            process_import_failure(job, session, storage, saved_storage_keys, error, cleanup_storage=True)
        return


def get_import_job(session: Session, job_id: str, owner_id: str, raise_error: bool = True) -> ImportJob | None:
    job = query_import_job(session, job_id, owner_id)
    if job is None and raise_error:
        raise ImportNotFoundError()
    return job
