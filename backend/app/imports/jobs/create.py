import logging
from dataclasses import dataclass

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    ActiveImportExistsError,
    ApiError,
    ImportCreationError,
)
from app.core.logging import bind_logger
from app.db.session import db_transaction
from app.imports.constants import (
    ACTIVE_IMPORT_STATUSES,
    IMPORT_LOG_COMPONENT,
)
from app.imports.events import build_job_event
from app.imports.queries import (
    count_import_jobs_by_statuses,
    get_import_job_by_dedupe_key,
)
from app.imports.request_validation import validate_import_request
from app.imports.storage_cleanup import cleanup_import_storage
from app.media.images import ValidatedImage
from app.models import (
    ImportEventType,
    ImportJob,
    ImportJobSource,
    ImportJobStatus,
    ImportSourceStatus,
    SourceType,
    new_id,
)
from app.notifications.notification_data import ImportStartedNotification, build_notification
from app.queueing.constants import QueueMessageType
from app.queueing.outbox import schedule_outbox_message
from app.storage.base import StorageService
from app.storage.constants import StorageLocation, StorageUserPurpose
from app.storage.runtime import get_storage_service
from app.storage.types import StorageUserContext

logger = bind_logger(logging.getLogger(__name__), component=IMPORT_LOG_COMPONENT)


@dataclass
class ImportJobCreationResult:
    job: ImportJob
    was_created: bool
    outbox_message_id: str | None


def _get_existing_import(
    session: Session,
    *,
    owner_id: str,
    dedupe_key: str,
    max_active_imports: int,
) -> ImportJob | None:
    existing = get_import_job_by_dedupe_key(session, owner_id, dedupe_key)
    if existing is not None:
        return existing
    active_import_count = count_import_jobs_by_statuses(session, owner_id, ACTIVE_IMPORT_STATUSES)
    if active_import_count >= max_active_imports:
        raise ActiveImportExistsError(max_active_imports=max_active_imports)
    return None


def _build_image_sources(
    storage: StorageService,
    images: list[ValidatedImage],
    *,
    owner_id: str,
    job_id: str,
) -> tuple[list[ImportJobSource], list[str]]:
    sources: list[ImportJobSource] = []
    storage_keys: list[str] = []
    context = StorageUserContext(
        owner_id=owner_id,
        purpose=StorageUserPurpose.IMPORT_SOURCE,
        entity_id=job_id,
    )
    for position, image in enumerate(images):
        try:
            saved = storage.save(
                StorageLocation.USER_MEDIA,
                image.content,
                image.original_name,
                image.mime_type,
                context=context,
            )
            storage_keys.append(saved.storage_key)
        except Exception as error:
            logger.error(
                "Primary import resource upload failed.",
                error=repr(error),
                resource_position=position,
                resource_type=SourceType.IMAGE.value,
                original_name=image.original_name,
                content_type=image.mime_type,
            )
            cleanup_import_storage(storage, StorageLocation.USER_MEDIA, storage_keys)
            raise
        sources.append(
            ImportJobSource(
                type=SourceType.IMAGE,
                status=ImportSourceStatus.READY,
                image_storage_key=saved.storage_key,
                original_name=saved.original_name,
                mime_type=saved.mime_type,
                size_bytes=saved.size_bytes,
                position=position,
            )
        )
    return sources, storage_keys


def _build_text_and_url_sources(
    text: str | None,
    url: str | None,
    *,
    start_position: int,
) -> list[ImportJobSource]:
    sources: list[ImportJobSource] = []
    if text is not None:
        sources.append(
            ImportJobSource(
                type=SourceType.TEXT,
                status=ImportSourceStatus.READY,
                text=text,
                position=start_position,
            )
        )
    if url is not None:
        sources.append(
            ImportJobSource(
                type=SourceType.URL,
                status=ImportSourceStatus.READY,
                url=url,
                position=start_position + len(sources),
            )
        )
    return sources


def _persist_import_job(
    session: Session,
    *,
    job_id: str,
    owner_id: str,
    client_id: str,
    client_import_id: str,
    dedupe_key: str,
    sources: list[ImportJobSource],
    max_active_imports: int,
) -> ImportJobCreationResult:
    with db_transaction(session):
        existing = _get_existing_import(
            session,
            owner_id=owner_id,
            dedupe_key=dedupe_key,
            max_active_imports=max_active_imports,
        )
        if existing is not None:
            return ImportJobCreationResult(job=existing, was_created=False, outbox_message_id=None)

        job = ImportJob(
            id=job_id,
            owner_id=owner_id,
            client_id=client_id,
            client_import_id=client_import_id,
            dedupe_key=dedupe_key,
            status=ImportJobStatus.QUEUED,
            sources=sources,
        )
        session.add(job)
        build_job_event(
            session,
            import_job_id=job.id,
            event_type=ImportEventType.IMPORT_CREATED,
            client_import_id=client_import_id,
            dedupe_key=dedupe_key,
        )
        build_notification(
            session,
            ImportStartedNotification,
            owner_id=job.owner_id,
            entity_id=job.id,
        )
        outbox_message = schedule_outbox_message(session, QueueMessageType.IMPORT_JOB, job.id)
    return ImportJobCreationResult(job=job, was_created=True, outbox_message_id=outbox_message.id)


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
    request = validate_import_request(text, url, files or [])

    normalized_idempotency_key = idempotency_key.strip()[:128] if idempotency_key else ""
    dedupe_key = normalized_idempotency_key or client_import_id
    settings = get_settings()

    storage: StorageService | None = None
    saved_storage_keys: list[str] = []
    uploads_attached_to_job = False
    job_id = new_id()
    try:
        with db_transaction(session):
            existing = _get_existing_import(
                session,
                owner_id=owner_id,
                dedupe_key=dedupe_key,
                max_active_imports=settings.max_parallel_imports_per_client,
            )
        if existing is not None:
            return ImportJobCreationResult(job=existing, was_created=False, outbox_message_id=None)

        storage = get_storage_service()
        sources, saved_storage_keys = _build_image_sources(
            storage,
            request.images,
            owner_id=owner_id,
            job_id=job_id,
        )
        sources.extend(
            _build_text_and_url_sources(
                request.text,
                request.url,
                start_position=len(sources),
            )
        )

        result = _persist_import_job(
            session,
            job_id=job_id,
            owner_id=owner_id,
            client_id=client_id,
            client_import_id=client_import_id,
            dedupe_key=dedupe_key,
            sources=sources,
            max_active_imports=settings.max_parallel_imports_per_client,
        )
        if not result.was_created:
            return result
        uploads_attached_to_job = True
    except IntegrityError as error:
        existing = get_import_job_by_dedupe_key(session, owner_id, dedupe_key)
        if existing is not None:
            return ImportJobCreationResult(job=existing, was_created=False, outbox_message_id=None)
        logger.error(
            "Import job creation failed after a uniqueness conflict.",
            owner_id=owner_id,
            client_import_id=client_import_id,
            dedupe_key=dedupe_key,
            error=repr(error),
        )
        raise ImportCreationError() from error
    except ApiError:
        raise
    except Exception as error:
        logger.error(
            "Import job creation failed.",
            owner_id=owner_id,
            client_id=client_id,
            client_import_id=client_import_id,
            dedupe_key=dedupe_key,
            error=repr(error),
        )
        raise ImportCreationError() from error
    finally:
        if storage is not None and saved_storage_keys and not uploads_attached_to_job:
            cleanup_import_storage(storage, StorageLocation.USER_MEDIA, saved_storage_keys)

    logger.info(
        "Import job was created.",
        job=result.job.to_dict(),
        has_text=request.text is not None,
        has_url=request.url is not None,
        attachment_count=len(request.images),
    )
    return result
