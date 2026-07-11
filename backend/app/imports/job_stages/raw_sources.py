import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import anyio

from app.core.logging import bind_logger, log_error
from app.imports.config import ImportConfig
from app.imports.constants import IMPORT_LOG_COMPONENT
from app.imports.error_codes import SecondaryResourceUploadError
from app.imports.job_context import ImportJobContext, ImportJobSourceContext
from app.imports.source_loading.types import UrlContentService
from app.imports.source_loading.url_loaders.types import LoadedUrlContent
from app.imports.source_loading.video_processors.types import FirstPassVideoSources, VideoSourceProcessor
from app.models import RecipeResourceOrigin, SourceType
from app.storage.base import StorageService

logger = logging.getLogger(IMPORT_LOG_COMPONENT)


@dataclass
class RawSource:
    type: SourceType
    source: RecipeResourceOrigin
    position: int
    parent_key: str | None = None
    key: str | None = None
    url: str | None = None
    text: str | None = None
    image_storage_key: str | None = None
    original_name: str | None = None
    mime_type: str | None = None
    image_bytes: bytes | None = None


@dataclass
class RawSourceBuildContext:
    job: ImportJobContext
    storage: StorageService
    secondary_storage_keys: list[str]
    url_content_loader: UrlContentService
    video_processor: VideoSourceProcessor
    config: ImportConfig


def build_raw_sources(
    job: ImportJobContext,
    storage: StorageService,
    secondary_storage_keys: list[str],
    url_content_loader: UrlContentService,
    video_processor: VideoSourceProcessor,
    import_config: ImportConfig,
) -> tuple[list[RawSource], str | None]:
    context = RawSourceBuildContext(
        job=job,
        storage=storage,
        secondary_storage_keys=secondary_storage_keys,
        url_content_loader=url_content_loader,
        video_processor=video_processor,
        config=import_config,
    )
    imported_author_name: str | None = None
    raw_sources: list[RawSource] = []
    for job_source in sorted(job.sources, key=lambda item: item.position):
        if job_source.type == SourceType.TEXT and job_source.text:
            raw_sources.append(
                RawSource(type=SourceType.TEXT, source=RecipeResourceOrigin.MANUAL, text=job_source.text, position=len(raw_sources))
            )
        elif job_source.type == SourceType.IMAGE and job_source.image_storage_key and job_source.mime_type:
            raw_sources.append(
                RawSource(
                    type=SourceType.IMAGE,
                    source=RecipeResourceOrigin.MANUAL,
                    image_storage_key=job_source.image_storage_key,
                    image_bytes=storage.read(job_source.image_storage_key),
                    mime_type=job_source.mime_type,
                    original_name=job_source.original_name or "upload",
                    position=len(raw_sources),
                )
            )
        elif job_source.type == SourceType.URL and job_source.url:
            url_author_name = _append_url_raw_sources(
                context,
                job_source,
                raw_sources,
            )
            if url_author_name and imported_author_name is None:
                imported_author_name = url_author_name
    return raw_sources, imported_author_name


def _append_url_raw_sources(
    context: RawSourceBuildContext,
    job_source: ImportJobSourceContext,
    raw_sources: list[RawSource],
) -> str | None:
    parent_key = f"url:{job_source.position}"
    raw_sources.append(
        RawSource(
            type=SourceType.URL,
            source=RecipeResourceOrigin.MANUAL,
            url=job_source.url,
            key=parent_key,
            position=len(raw_sources),
        )
    )
    image_count = len([raw_source for raw_source in raw_sources if raw_source.type == SourceType.IMAGE])
    remaining_images = max(0, context.config.max_import_images - image_count)
    bind_logger(
        logger,
        component=IMPORT_LOG_COMPONENT,
        job=context.job.to_dict(),
        accepted_attachment_count=image_count,
        remaining_remote_image_count=remaining_images,
    ).info(f"{IMPORT_LOG_COMPONENT} Import image capacity")
    try:
        loaded_url = anyio.run(
            context.url_content_loader.load,
            job_source.url,
            remaining_images,
            context.config.max_upload_bytes,
        )
    except Exception as error:
        raise SecondaryResourceUploadError(
            exception=repr(error),
            resource_type=SourceType.URL.value,
            url=job_source.url,
        ) from error
    raw_sources[-1].url = loaded_url.url
    raw_sources.append(
        RawSource(
            type=SourceType.TEXT,
            source=RecipeResourceOrigin.URL,
            parent_key=parent_key,
            text=loaded_url.text,
            position=len(raw_sources),
        )
    )
    for remote_image in loaded_url.images[:remaining_images]:
        try:
            saved = context.storage.save(remote_image.bytes, remote_image.original_name, remote_image.mime_type)
        except Exception as error:
            raise SecondaryResourceUploadError(
                exception=repr(error),
                resource_type=SourceType.IMAGE.value,
                url=job_source.url,
                original_name=remote_image.original_name,
                mime_type=remote_image.mime_type,
            ) from error
        context.secondary_storage_keys.append(saved.storage_key)
        raw_sources.append(
            RawSource(
                type=SourceType.IMAGE,
                source=RecipeResourceOrigin.URL,
                parent_key=parent_key,
                image_storage_key=saved.storage_key,
                image_bytes=remote_image.bytes,
                mime_type=remote_image.mime_type,
                original_name=remote_image.original_name,
                position=len(raw_sources),
            )
        )
    _append_url_video_raw_sources(context, loaded_url, parent_key, raw_sources)
    return loaded_url.author_name


def _append_url_video_raw_sources(
    context: RawSourceBuildContext,
    loaded_url: LoadedUrlContent,
    parent_key: str,
    raw_sources: list[RawSource],
) -> None:
    loaded_videos = loaded_url.videos[: context.config.max_import_videos]
    if not loaded_videos:
        return

    started_at = datetime.now(timezone.utc)
    try:
        first_pass_video_sources = _coerce_first_pass_video_sources(
            anyio.run(
                _prepare_first_pass_video_sources,
                context.video_processor,
                loaded_videos,
                context.config.max_upload_bytes,
                context.config.max_video_bytes,
            )
        )
    except Exception as error:
        log_error(
            logger,
            f"{IMPORT_LOG_COMPONENT} Video first-pass processing failed",
            component=IMPORT_LOG_COMPONENT,
            job=context.job.to_dict(),
            video_count=len(loaded_videos),
            error=repr(error),
        )
        raise SecondaryResourceUploadError(
            exception=repr(error),
            resource_type="VIDEO",
            video_count=len(loaded_videos),
        ) from error
    trimmed_transcript = (first_pass_video_sources.transcript_text or "").strip()
    bind_logger(
        logger,
        component=IMPORT_LOG_COMPONENT,
        job=context.job.to_dict(),
        video_count=len(loaded_videos),
        poster_image_count=len(first_pass_video_sources.poster_images),
        has_transcript=bool(trimmed_transcript),
        transcript_char_count=len(trimmed_transcript),
        duration_ms=int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000),
    ).info(f"{IMPORT_LOG_COMPONENT} Video first-pass processed")
    if trimmed_transcript:
        raw_sources.append(
            RawSource(
                type=SourceType.TEXT,
                source=RecipeResourceOrigin.URL_VIDEO,
                parent_key=parent_key,
                text=trimmed_transcript,
                position=len(raw_sources),
            )
    )
    for poster in first_pass_video_sources.poster_images:
        image_count = len([raw_source for raw_source in raw_sources if raw_source.type == SourceType.IMAGE])
        if image_count >= context.config.max_import_images:
            break
        try:
            saved = context.storage.save(poster.bytes, poster.original_name, poster.mime_type)
        except Exception as error:
            raise SecondaryResourceUploadError(
                exception=repr(error),
                resource_type="VIDEO_POSTER",
                original_name=poster.original_name,
                mime_type=poster.mime_type,
            ) from error
        context.secondary_storage_keys.append(saved.storage_key)
        raw_sources.append(
            RawSource(
                type=SourceType.IMAGE,
                source=RecipeResourceOrigin.URL_VIDEO,
                parent_key=parent_key,
                image_storage_key=saved.storage_key,
                image_bytes=poster.bytes,
                mime_type=poster.mime_type,
                original_name=poster.original_name,
                position=len(raw_sources),
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
