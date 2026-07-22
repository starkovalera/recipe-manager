import logging
from dataclasses import dataclass
from io import BytesIO

from fastapi import UploadFile
from PIL import Image
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    ActiveImportExistsError,
    ApiError,
    FileTooLargeError,
    ImportCreationError,
    InvalidFileTypeError,
    NoImportSourcesError,
    TextTooLongError,
    TooManyFilesError,
)
from app.core.logging import bind_logger
from app.db.session import db_transaction
from app.imports.constants import (
    ACTIVE_IMPORT_STATUSES,
    IMPORT_LOG_COMPONENT,
    SUPPORTED_UPLOAD_TYPES,
)
from app.imports.events import build_job_event
from app.imports.queries import (
    count_import_jobs_by_statuses,
    get_import_job_by_dedupe_key,
)
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
from app.storage.constants import StorageLocation, StoragePurpose
from app.storage.runtime import get_storage_service
from app.storage.types import StorageWriteContext

logger = bind_logger(logging.getLogger(__name__), component=IMPORT_LOG_COMPONENT)


@dataclass
class ImportJobCreationResult:
    job: ImportJob
    was_created: bool
    outbox_message_id: str | None


def _validate_import_request(
    text: str | None,
    url: str | None,
    files: list[UploadFile],
) -> tuple[str | None, str | None, list[ValidatedImage]]:
    settings = get_settings()
    normalized_text = text.strip() if text else None
    normalized_url = url.strip() if url else None
    validated_images = []

    if not normalized_text and not normalized_url and not files:
        raise NoImportSourcesError()

    if normalized_text and len(normalized_text) > settings.max_import_text_chars:
        raise TextTooLongError(max_length=settings.max_import_text_chars)

    if len(files) > settings.max_import_images:
        raise TooManyFilesError(max_files=settings.max_import_images)

    for upload in files:
        content_type = upload.content_type or ""
        original_filename = upload.filename or "upload"
        if content_type not in SUPPORTED_UPLOAD_TYPES:
            raise InvalidFileTypeError(content_type=content_type, filename=original_filename)

        content = upload.file.read()
        if len(content) > settings.max_upload_bytes:
            raise FileTooLargeError(max_size_bytes=settings.max_upload_bytes)
        try:
            with Image.open(BytesIO(content)) as image:
                image.verify()
        except (OSError, ValueError) as error:
            raise InvalidFileTypeError(
                content_type=content_type,
                filename=original_filename,
                original_error=str(error),
            ) from error
        validated_images.append(
            ValidatedImage(
                content=content,
                mime_type=content_type,
                original_name=original_filename,
            )
        )
    return normalized_text, normalized_url, validated_images


def _preflight_import_creation(
    session: Session,
    owner_id: str,
    dedupe_key: str,
    max_active_imports: int,
) -> ImportJob | None:
    with db_transaction(session):
        existing = get_import_job_by_dedupe_key(session, owner_id, dedupe_key)
        if existing is not None:
            return existing
        active_import_count = count_import_jobs_by_statuses(session, owner_id, ACTIVE_IMPORT_STATUSES)
        if active_import_count >= max_active_imports:
            raise ActiveImportExistsError(max_active_imports=max_active_imports)
    return None


def _upload_primary_sources(
    storage: StorageService,
    images: list[ValidatedImage],
    *,
    owner_id: str,
    job_id: str,
) -> tuple[list[ImportJobSource], list[str]]:
    sources: list[ImportJobSource] = []
    storage_keys: list[str] = []
    context = StorageWriteContext(
        owner_id=owner_id,
        purpose=StoragePurpose.IMPORT_SOURCE,
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
) -> tuple[ImportJob, str | None, bool]:
    with db_transaction(session):
        existing = get_import_job_by_dedupe_key(session, owner_id, dedupe_key)
        if existing is not None:
            return existing, None, False
        active_import_count = count_import_jobs_by_statuses(session, owner_id, ACTIVE_IMPORT_STATUSES)
        if active_import_count >= max_active_imports:
            raise ActiveImportExistsError(max_active_imports=max_active_imports)

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
    return job, outbox_message.id, True


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
    normalized_text, normalized_url, validated_images = _validate_import_request(text, url, files or [])

    normalized_idempotency_key = idempotency_key.strip()[:128] if idempotency_key else ""
    dedupe_key = normalized_idempotency_key or client_import_id
    settings = get_settings()

    existing = _preflight_import_creation(
        session,
        owner_id,
        dedupe_key,
        settings.max_parallel_imports_per_client,
    )
    if existing is not None:
        return ImportJobCreationResult(job=existing, was_created=False, outbox_message_id=None)

    storage: StorageService | None = None
    saved_storage_keys: list[str] = []
    job_id = new_id()
    try:
        storage = get_storage_service()
        sources, saved_storage_keys = _upload_primary_sources(
            storage,
            validated_images,
            owner_id=owner_id,
            job_id=job_id,
        )
        resource_position = len(sources)
        if normalized_text:
            sources.append(
                ImportJobSource(
                    type=SourceType.TEXT,
                    status=ImportSourceStatus.READY,
                    text=normalized_text,
                    position=resource_position,
                )
            )
            resource_position += 1
        if normalized_url:
            sources.append(
                ImportJobSource(
                    type=SourceType.URL,
                    status=ImportSourceStatus.READY,
                    url=normalized_url,
                    position=resource_position,
                )
            )

        job, outbox_message_id, was_created = _persist_import_job(
            session,
            job_id=job_id,
            owner_id=owner_id,
            client_id=client_id,
            client_import_id=client_import_id,
            dedupe_key=dedupe_key,
            sources=sources,
            max_active_imports=settings.max_parallel_imports_per_client,
        )
        if not was_created:
            cleanup_import_storage(storage, StorageLocation.USER_MEDIA, saved_storage_keys)
            return ImportJobCreationResult(job=job, was_created=False, outbox_message_id=None)
    except IntegrityError as error:
        if storage is not None:
            cleanup_import_storage(storage, StorageLocation.USER_MEDIA, saved_storage_keys)
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
        if storage is not None and saved_storage_keys:
            cleanup_import_storage(storage, StorageLocation.USER_MEDIA, saved_storage_keys)
        raise
    except Exception as error:
        if storage is not None:
            cleanup_import_storage(storage, StorageLocation.USER_MEDIA, saved_storage_keys)
        logger.error(
            "Import job creation failed.",
            owner_id=owner_id,
            client_id=client_id,
            client_import_id=client_import_id,
            dedupe_key=dedupe_key,
            error=repr(error),
        )
        raise ImportCreationError() from error

    logger.info(
        "Import job was created.",
        job=job.to_dict(),
        has_text=normalized_text is not None,
        has_url=normalized_url is not None,
        attachment_count=len(validated_images),
    )
    return ImportJobCreationResult(
        job=job,
        was_created=True,
        outbox_message_id=outbox_message_id,
    )
