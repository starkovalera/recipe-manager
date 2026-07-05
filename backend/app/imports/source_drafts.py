import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import anyio

from app.core.logging import bind_logger, log_error
from app.imports.constants import IMPORT_LOG_COMPONENT, IMPORT_LOG_PREFIX
from app.imports.error_codes import ImportProcessingError, ImportProcessingErrorCode
from app.imports.recipe_builder import SourceDraft
from app.imports.url_loaders.types import LoadedUrlContent
from app.imports.video import FirstPassVideoSources
from app.models import ImportJob, ImportJobSource, RecipeResourceOrigin, SourceType
from app.storage.local import LocalStorageService


class ImportSettings(Protocol):
    max_import_images: int
    max_import_videos: int
    max_upload_bytes: int
    max_video_bytes: int


class UrlContentLoader(Protocol):
    async def load(self, url: str, max_images: int, max_image_bytes: int) -> LoadedUrlContent: ...


class VideoSourceProcessor(Protocol):
    async def prepare_first_pass_video_sources(self, *, videos, max_image_bytes: int, max_video_bytes: int): ...


@dataclass
class SourceDraftBuildContext:
    job: ImportJob
    storage: LocalStorageService
    saved_storage_keys: list[str]
    url_content_loader: UrlContentLoader
    video_processor: VideoSourceProcessor
    settings: ImportSettings
    logger: logging.Logger


def build_source_drafts_for_job(
    job: ImportJob,
    storage: LocalStorageService,
    saved_storage_keys: list[str],
    url_content_loader: UrlContentLoader,
    video_processor: VideoSourceProcessor,
    settings: ImportSettings,
    logger: logging.Logger,
) -> tuple[list[SourceDraft], str | None]:
    context = SourceDraftBuildContext(
        job=job,
        storage=storage,
        saved_storage_keys=saved_storage_keys,
        url_content_loader=url_content_loader,
        video_processor=video_processor,
        settings=settings,
        logger=logger,
    )
    source_drafts: list[SourceDraft] = []
    imported_author_name: str | None = None
    for source in sorted(job.sources, key=lambda item: item.position):
        if source.type == SourceType.TEXT and source.text:
            source_drafts.append(
                SourceDraft(type=SourceType.TEXT, source=RecipeResourceOrigin.MANUAL, text=source.text, position=len(source_drafts))
            )
        elif source.type == SourceType.IMAGE and source.image_storage_key and source.mime_type:
            source_drafts.append(
                SourceDraft(
                    type=SourceType.IMAGE,
                    source=RecipeResourceOrigin.MANUAL,
                    image_storage_key=source.image_storage_key,
                    image_bytes=context.storage.read(source.image_storage_key),
                    mime_type=source.mime_type,
                    original_name=source.original_name or "upload",
                    position=len(source_drafts),
                )
            )
        elif source.type == SourceType.URL and source.url:
            url_author_name = _append_url_source_drafts(
                context,
                source,
                source_drafts,
            )
            if url_author_name and imported_author_name is None:
                imported_author_name = url_author_name
    return source_drafts, imported_author_name


def _append_url_source_drafts(
    context: SourceDraftBuildContext,
    source: ImportJobSource,
    source_drafts: list[SourceDraft],
) -> str | None:
    parent_key = f"url:{source.position}"
    source_drafts.append(
        SourceDraft(
            type=SourceType.URL,
            source=RecipeResourceOrigin.MANUAL,
            url=source.url,
            key=parent_key,
            position=len(source_drafts),
        )
    )
    image_count = len([draft for draft in source_drafts if draft.type == SourceType.IMAGE])
    remaining_images = max(0, context.settings.max_import_images - image_count)
    bind_logger(
        context.logger,
        component=IMPORT_LOG_COMPONENT,
        ownerId=context.job.owner_id,
        importJobId=context.job.id,
        acceptedAttachmentCount=image_count,
        remainingRemoteImageCount=remaining_images,
    ).info(f"{IMPORT_LOG_PREFIX} Import image capacity")
    try:
        loaded_url = anyio.run(
            context.url_content_loader.load,
            source.url,
            remaining_images,
            context.settings.max_upload_bytes,
        )
    except Exception as error:
        raise ImportProcessingError(
            ImportProcessingErrorCode.SECONDARY_RESOURCE_UPLOADING_FAILED,
            diagnostic_message=repr(error),
            payload={"resourceType": SourceType.URL.value, "url": source.url},
        ) from error
    source_drafts[-1].url = loaded_url.url
    source_drafts.append(
        SourceDraft(
            type=SourceType.TEXT,
            source=RecipeResourceOrigin.URL,
            parent_key=parent_key,
            text=loaded_url.text,
            position=len(source_drafts),
        )
    )
    for remote_image in loaded_url.images[:remaining_images]:
        try:
            saved = context.storage.save(remote_image.bytes, remote_image.original_name, remote_image.mime_type)
        except Exception as error:
            raise ImportProcessingError(
                ImportProcessingErrorCode.SECONDARY_RESOURCE_UPLOADING_FAILED,
                diagnostic_message=repr(error),
                payload={
                    "resourceType": SourceType.IMAGE.value,
                    "url": source.url,
                    "originalName": remote_image.original_name,
                    "mimeType": remote_image.mime_type,
                },
            ) from error
        context.saved_storage_keys.append(saved.storage_key)
        source_drafts.append(
            SourceDraft(
                type=SourceType.IMAGE,
                source=RecipeResourceOrigin.URL,
                parent_key=parent_key,
                image_storage_key=saved.storage_key,
                image_bytes=remote_image.bytes,
                mime_type=remote_image.mime_type,
                original_name=remote_image.original_name,
                position=len(source_drafts),
            )
        )
    _append_url_video_source_drafts(context, loaded_url, parent_key, source_drafts)
    return loaded_url.author_name


def _append_url_video_source_drafts(
    context: SourceDraftBuildContext,
    loaded_url: LoadedUrlContent,
    parent_key: str,
    source_drafts: list[SourceDraft],
) -> None:
    loaded_videos = loaded_url.videos[: context.settings.max_import_videos]
    if not loaded_videos:
        return

    started_at = datetime.now(timezone.utc)
    try:
        first_pass_video_sources = _coerce_first_pass_video_sources(
            anyio.run(
                _prepare_first_pass_video_sources,
                context.video_processor,
                loaded_videos,
                context.settings.max_upload_bytes,
                context.settings.max_video_bytes,
            )
        )
    except Exception as error:
        log_error(
            context.logger,
            f"{IMPORT_LOG_PREFIX} Video first-pass processing failed",
            component=IMPORT_LOG_COMPONENT,
            ownerId=context.job.owner_id,
            importJobId=context.job.id,
            videoCount=len(loaded_videos),
            error=repr(error),
        )
        raise ImportProcessingError(
            ImportProcessingErrorCode.SECONDARY_RESOURCE_UPLOADING_FAILED,
            diagnostic_message=repr(error),
            payload={"resourceType": "VIDEO", "videoCount": len(loaded_videos)},
        ) from error
    trimmed_transcript = (first_pass_video_sources.transcript_text or "").strip()
    bind_logger(
        context.logger,
        component=IMPORT_LOG_COMPONENT,
        ownerId=context.job.owner_id,
        importJobId=context.job.id,
        videoCount=len(loaded_videos),
        posterImageCount=len(first_pass_video_sources.poster_images),
        hasTranscript=bool(trimmed_transcript),
        transcriptCharCount=len(trimmed_transcript),
        durationMs=int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000),
    ).info(f"{IMPORT_LOG_PREFIX} Video first-pass processed")
    if trimmed_transcript:
        source_drafts.append(
            SourceDraft(
                type=SourceType.TEXT,
                source=RecipeResourceOrigin.URL_VIDEO,
                parent_key=parent_key,
                text=trimmed_transcript,
                position=len(source_drafts),
            )
    )
    for poster in first_pass_video_sources.poster_images:
        image_count = len([draft for draft in source_drafts if draft.type == SourceType.IMAGE])
        if image_count >= context.settings.max_import_images:
            break
        try:
            saved = context.storage.save(poster.bytes, poster.original_name, poster.mime_type)
        except Exception as error:
            raise ImportProcessingError(
                ImportProcessingErrorCode.SECONDARY_RESOURCE_UPLOADING_FAILED,
                diagnostic_message=repr(error),
                payload={
                    "resourceType": "VIDEO_POSTER",
                    "originalName": poster.original_name,
                    "mimeType": poster.mime_type,
                },
            ) from error
        context.saved_storage_keys.append(saved.storage_key)
        source_drafts.append(
            SourceDraft(
                type=SourceType.IMAGE,
                source=RecipeResourceOrigin.URL_VIDEO,
                parent_key=parent_key,
                image_storage_key=saved.storage_key,
                image_bytes=poster.bytes,
                mime_type=poster.mime_type,
                original_name=poster.original_name,
                position=len(source_drafts),
            )
        )


def _coerce_first_pass_video_sources(value) -> FirstPassVideoSources:
    if isinstance(value, FirstPassVideoSources):
        return value
    return FirstPassVideoSources(
        poster_images=list(value.get("poster_images") or []),
        transcript_text=value.get("transcript_text"),
    )


async def _prepare_first_pass_video_sources(
    video_processor: VideoSourceProcessor,
    videos,
    max_image_bytes: int,
    max_video_bytes: int,
):
    return await video_processor.prepare_first_pass_video_sources(
        videos=videos,
        max_image_bytes=max_image_bytes,
        max_video_bytes=max_video_bytes,
    )
