import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import anyio

from app.core.logging import bind_logger, log_error
from app.imports.config import ImportConfig
from app.imports.constants import IMPORT_LOG_COMPONENT
from app.imports.error_codes import SecondaryResourceUploadError
from app.imports.job_context import ImportJobContext, ImportJobSourceContext
from app.imports.source_loading.results import (
    SecondaryResourceKind,
    SecondaryResourceLoadResult,
    SecondaryResourceLoadStatus,
)
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


@dataclass(frozen=True)
class RawSourcesBuildResult:
    raw_sources: list[RawSource]
    imported_author_name: str | None
    secondary_resource_results: list[SecondaryResourceLoadResult]

    @property
    def failed_secondary_resources(self) -> list[SecondaryResourceLoadResult]:
        return [result for result in self.secondary_resource_results if result.status == SecondaryResourceLoadStatus.FAILED]


@dataclass(frozen=True)
class UrlRawSourcesResult:
    author_name: str | None
    secondary_resource_results: list[SecondaryResourceLoadResult]


def build_raw_sources(
    job: ImportJobContext,
    storage: StorageService,
    secondary_storage_keys: list[str],
    url_content_loader: UrlContentService,
    video_processor: VideoSourceProcessor,
    import_config: ImportConfig,
) -> RawSourcesBuildResult:
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
    secondary_resource_results: list[SecondaryResourceLoadResult] = []
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
            url_result = _append_url_raw_sources(
                context,
                job_source,
                raw_sources,
            )
            secondary_resource_results.extend(url_result.secondary_resource_results)
            if url_result.author_name and imported_author_name is None:
                imported_author_name = url_result.author_name

    failed_secondary_resources = [result for result in secondary_resource_results if result.status == SecondaryResourceLoadStatus.FAILED]
    skipped_secondary_resources = [result for result in secondary_resource_results if result.status == SecondaryResourceLoadStatus.SKIPPED]
    if failed_secondary_resources:
        log_error(
            logger,
            f"{IMPORT_LOG_COMPONENT} Secondary resource loading completed with failures",
            component=IMPORT_LOG_COMPONENT,
            job=context.job.to_dict(),
            resources=[result.to_dict() for result in failed_secondary_resources],
        )
    if skipped_secondary_resources:
        bind_logger(logger, component=IMPORT_LOG_COMPONENT, job=context.job.to_dict()).info(
            f"{IMPORT_LOG_COMPONENT} Secondary resources skipped",
            resources=[result.to_dict() for result in skipped_secondary_resources],
        )

    _validate_single_url_secondary_sources(job, raw_sources, secondary_resource_results)
    return RawSourcesBuildResult(
        raw_sources=raw_sources,
        imported_author_name=imported_author_name,
        secondary_resource_results=secondary_resource_results,
    )


def _append_url_raw_sources(
    context: RawSourceBuildContext,
    job_source: ImportJobSourceContext,
    raw_sources: list[RawSource],
) -> UrlRawSourcesResult:
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
    secondary_resource_results: list[SecondaryResourceLoadResult] = []
    try:
        loaded_url = anyio.run(
            context.url_content_loader.load,
            job_source.url,
            remaining_images,
            context.config.max_upload_bytes,
        )
    except Exception as error:
        secondary_resource_results.append(
            SecondaryResourceLoadResult(
                kind=SecondaryResourceKind.URL_CONTENT,
                status=SecondaryResourceLoadStatus.FAILED,
                url=job_source.url,
                error=repr(error),
            )
        )
        return UrlRawSourcesResult(
            author_name=None,
            secondary_resource_results=secondary_resource_results,
        )
    raw_sources[-1].url = loaded_url.url
    secondary_resource_results.extend(loaded_url.resource_results)
    loaded_text = (loaded_url.text or "").strip()
    secondary_resource_results.append(
        SecondaryResourceLoadResult(
            kind=SecondaryResourceKind.TEXT,
            status=(SecondaryResourceLoadStatus.LOADED if loaded_text else SecondaryResourceLoadStatus.SKIPPED),
            url=loaded_url.url,
        )
    )
    if loaded_text:
        raw_sources.append(
            RawSource(
                type=SourceType.TEXT,
                source=RecipeResourceOrigin.URL,
                parent_key=parent_key,
                text=loaded_text,
                position=len(raw_sources),
            )
        )
    for remote_image in loaded_url.images[:remaining_images]:
        try:
            saved = context.storage.save(remote_image.bytes, remote_image.original_name, remote_image.mime_type)
        except Exception as error:
            secondary_resource_results.append(
                SecondaryResourceLoadResult(
                    kind=SecondaryResourceKind.IMAGE,
                    status=SecondaryResourceLoadStatus.FAILED,
                    position=remote_image.position,
                    url=remote_image.url,
                    original_name=remote_image.original_name,
                    error=repr(error),
                )
            )
            continue
        secondary_resource_results.append(
            SecondaryResourceLoadResult(
                kind=SecondaryResourceKind.IMAGE,
                status=SecondaryResourceLoadStatus.LOADED,
                position=remote_image.position,
                url=remote_image.url,
                original_name=remote_image.original_name,
            )
        )
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
    secondary_resource_results.extend(_append_url_video_raw_sources(context, loaded_url, parent_key, raw_sources))
    return UrlRawSourcesResult(
        author_name=loaded_url.author_name,
        secondary_resource_results=secondary_resource_results,
    )


def _append_url_video_raw_sources(
    context: RawSourceBuildContext,
    loaded_url: LoadedUrlContent,
    parent_key: str,
    raw_sources: list[RawSource],
) -> list[SecondaryResourceLoadResult]:
    loaded_videos = loaded_url.videos[: context.config.max_import_videos]
    if not loaded_videos:
        return []

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
        return [
            SecondaryResourceLoadResult(
                kind=SecondaryResourceKind.VIDEO_TRANSCRIPT,
                status=SecondaryResourceLoadStatus.FAILED,
                position=video.position,
                url=video.url,
                original_name=video.original_name,
                error=repr(error),
            )
            for video in loaded_videos
        ]
    secondary_resource_results = list(first_pass_video_sources.resource_results)
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
            secondary_resource_results.append(
                SecondaryResourceLoadResult(
                    kind=SecondaryResourceKind.VIDEO_POSTER,
                    status=SecondaryResourceLoadStatus.FAILED,
                    position=poster.position,
                    url=poster.url,
                    original_name=poster.original_name,
                    error=repr(error),
                )
            )
            continue
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
    return secondary_resource_results


def _coerce_first_pass_video_sources(value) -> FirstPassVideoSources:
    if isinstance(value, FirstPassVideoSources):
        return value
    return FirstPassVideoSources(
        poster_images=list(value.get("poster_images") or []),
        transcript_text=value.get("transcript_text"),
        resource_results=list(value.get("resource_results") or []),
    )


def _validate_single_url_secondary_sources(
    job: ImportJobContext,
    raw_sources: list[RawSource],
    secondary_resource_results: list[SecondaryResourceLoadResult],
) -> None:
    if len(job.sources) != 1 or job.sources[0].type != SourceType.URL:
        return

    secondary_sources = [source for source in raw_sources if source.parent_key is not None]
    useful_sources = [
        source for source in secondary_sources if not (source.type == SourceType.IMAGE and source.source == RecipeResourceOrigin.URL_VIDEO)
    ]
    if useful_sources:
        return

    failed_resources = [result for result in secondary_resource_results if result.status == SecondaryResourceLoadStatus.FAILED]
    raise SecondaryResourceUploadError(
        reason="NO_USABLE_SECONDARY_RESOURCES",
        failed_resource_count=len(failed_resources),
        resources=[result.to_dict() for result in failed_resources],
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
