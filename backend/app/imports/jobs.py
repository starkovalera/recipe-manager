from datetime import datetime, timezone
import logging
from dataclasses import dataclass

import anyio
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import UploadFile

from app.ai.factory import create_recipe_extraction_provider
from app.ai.provider import RecipeExtractionProvider
from app.ai.schemas import ReadySource
from app.core.errors import ApiError, ErrorCode
from app.core.logging import log_error, log_info
from app.imports.cover_guard import CoverCandidate as ImportCoverCandidate
from app.imports.cover_guard import CoverGuardInput, choose_cover_candidate
from app.imports.source_platform import derive_source_name
from app.imports.sources import normalize_quality_source_refs, normalize_single_url_quality, source_assessments
from app.imports.sources import review_reason_codes, should_create_primary_review_flag
from app.imports.video import FirstPassVideoSources, VideoProcessor
from app.core.config import get_settings
from app.media.images import create_cover_image, image_to_data_url, validate_image_upload
from app.imports.url_loaders.generic import GenericUrlContentLoader
from app.imports.url_loaders.instagram import InstagramUrlContentLoader
from app.imports.url_loaders.registry import UrlContentLoaderRegistry
from app.imports.url_loaders.threads import ThreadsUrlContentLoader
from app.imports.url_loaders.types import LoadedUrlContent
from app.models import (
    ImportJob,
    ImportJobSource,
    ImportJobStatus,
    ImportSourceStatus,
    CoverImageSource,
    Ingredient,
    Recipe,
    RecipeImage,
    RecipeImageRole,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    RecipeReviewFlagType,
    RecipeSource,
    RecipeSourceOrigin,
    RecipeSourceStatus,
    SourceType,
)
from app.schemas.imports import ImportJobOut
from app.storage.local import LocalStorageService


logger = logging.getLogger("recipes.import")


@dataclass
class SourceDraft:
    type: SourceType
    source: RecipeSourceOrigin
    position: int
    parent_key: str | None = None
    key: str | None = None
    url: str | None = None
    text: str | None = None
    image_storage_key: str | None = None
    original_name: str | None = None
    mime_type: str | None = None
    image_bytes: bytes | None = None


def serialize_import_job(job: ImportJob) -> ImportJobOut:
    return ImportJobOut(
        jobId=job.id,
        status=job.status.value,
        createdRecipeId=job.created_recipe_id,
        errorCode=job.error_code,
        errorMessage=job.error_message,
        createdAt=job.created_at,
        startedAt=job.started_at,
        finishedAt=job.finished_at,
    )


SUPPORTED_UPLOAD_TYPES = {"image/jpeg", "image/png", "image/webp"}


class UrlContentRegistryProtocol:
    async def load(self, url: str, max_images: int, max_image_bytes: int) -> LoadedUrlContent:
        raise NotImplementedError


class DefaultUrlContentRegistry:
    def __init__(self):
        self.registry = UrlContentLoaderRegistry(
            [InstagramUrlContentLoader(), ThreadsUrlContentLoader(), GenericUrlContentLoader()]
        )

    async def load(self, url: str, max_images: int, max_image_bytes: int) -> LoadedUrlContent:
        return await self.registry.loader_for(url).load(
            url,
            max_images=max_images,
            max_image_bytes=max_image_bytes,
            max_videos=get_settings().max_import_videos,
        )


_url_content_loader_registry: UrlContentRegistryProtocol = DefaultUrlContentRegistry()
_recipe_extraction_provider_override: RecipeExtractionProvider | None = None
_video_processor_override = None


def set_url_content_loader_registry(registry: UrlContentRegistryProtocol) -> None:
    global _url_content_loader_registry
    _url_content_loader_registry = registry


def set_recipe_extraction_provider(provider: RecipeExtractionProvider) -> None:
    global _recipe_extraction_provider_override
    _recipe_extraction_provider_override = provider


def reset_recipe_extraction_provider() -> None:
    global _recipe_extraction_provider_override
    _recipe_extraction_provider_override = None


def set_video_processor(processor) -> None:
    global _video_processor_override
    _video_processor_override = processor


def reset_video_processor() -> None:
    global _video_processor_override
    _video_processor_override = None


def _recipe_extraction_provider() -> tuple[str, RecipeExtractionProvider]:
    if _recipe_extraction_provider_override is not None:
        return "test", _recipe_extraction_provider_override
    return create_recipe_extraction_provider(get_settings())


def _video_processor():
    return _video_processor_override or VideoProcessor(get_settings())


def _coerce_first_pass_video_sources(value) -> FirstPassVideoSources:
    if isinstance(value, FirstPassVideoSources):
        return value
    return FirstPassVideoSources(
        poster_images=list(value.get("poster_images") or []),
        transcript_text=value.get("transcript_text"),
    )


async def _prepare_first_pass_video_sources(processor, videos, max_image_bytes: int, max_video_bytes: int):
    return await processor.prepare_first_pass_video_sources(
        videos=videos,
        max_image_bytes=max_image_bytes,
        max_video_bytes=max_video_bytes,
    )


def _cleanup_storage_keys(storage: LocalStorageService, storage_keys: list[str]) -> None:
    for storage_key in storage_keys:
        storage.delete(storage_key)


def _status_from_assessment(status: str) -> RecipeSourceStatus:
    return RecipeSourceStatus(status)


def _apply_source_statuses(
    recipe_sources: list[RecipeSource],
    final_sources: list[RecipeSource],
    quality,
    ai_id_by_source: dict[RecipeSource, str],
) -> bool:
    assessments = source_assessments([ai_id_by_source[source] for source in final_sources], quality)
    for source in final_sources:
        assessment = assessments[ai_id_by_source[source]]
        source.status = _status_from_assessment(assessment.status)
        source.assessment_reason = assessment.reason
        source.assessment_confidence = assessment.confidence

    for source in recipe_sources:
        if source.parent is not None or source.type != SourceType.URL:
            continue
        children = [child for child in recipe_sources if child.parent is source]
        if not children:
            source.status = RecipeSourceStatus.UNKNOWN
        elif any(child.status == RecipeSourceStatus.USED for child in children):
            source.status = RecipeSourceStatus.USED
            source.assessment_reason = "At least one child source was selected as primary evidence by AI."
            source.assessment_confidence = quality.confidence
        elif all(child.status == RecipeSourceStatus.IGNORED for child in children):
            source.status = RecipeSourceStatus.IGNORED
            source.assessment_reason = "All child sources were ignored by AI."
            source.assessment_confidence = quality.confidence
        else:
            source.status = RecipeSourceStatus.UNKNOWN
            source.assessment_reason = None
            source.assessment_confidence = None

    return any(source.parent is None and source.status == RecipeSourceStatus.IGNORED for source in recipe_sources)


def _cover_candidate_ref(source_ref: str | None, accepted_refs: set[str]) -> str | None:
    if source_ref is None:
        return None
    if source_ref in accepted_refs:
        return source_ref
    if source_ref.startswith("image:"):
        unprefixed_ref = source_ref.removeprefix("image:")
        if unprefixed_ref in accepted_refs:
            return unprefixed_ref
    image_ref = f"image:{source_ref}"
    return image_ref if image_ref in accepted_refs else None


def _validate_import_request(text: str | None, url: str | None, files: list[UploadFile]) -> tuple[str | None, str | None]:
    settings = get_settings()
    normalized_text = text.strip() if text else None
    normalized_url = url.strip() if url else None
    if normalized_text and len(normalized_text) > settings.max_import_text_chars:
        raise ApiError(ErrorCode.TEXT_TOO_LONG, f"Text input supports up to {settings.max_import_text_chars} characters.")
    if len(files) > settings.max_import_images:
        raise ApiError(ErrorCode.TOO_MANY_FILES, f"Upload up to {settings.max_import_images} images.")
    for upload in files:
        if upload.content_type not in SUPPORTED_UPLOAD_TYPES:
            raise ApiError(ErrorCode.INVALID_FILE_TYPE, "Upload JPEG, PNG, or WebP images.")
    if not normalized_text and not normalized_url and not files:
        raise ApiError(ErrorCode.NOT_A_RECIPE, "Add a recipe URL, upload at least one recipe image, or add recipe text.")
    return normalized_text, normalized_url


def create_import_job(
    session: Session,
    owner_id: str,
    client_id: str,
    client_import_id: str,
    text: str | None,
    url: str | None,
    files: list[UploadFile] | None = None,
) -> ImportJob:
    files = files or []
    normalized_text, normalized_url = _validate_import_request(text, url, files)

    existing = session.scalar(select(ImportJob).where(ImportJob.owner_id == owner_id, ImportJob.client_import_id == client_import_id))
    if existing is not None:
        return existing

    job = ImportJob(owner_id=owner_id, client_id=client_id, client_import_id=client_import_id, status=ImportJobStatus.PENDING)
    position = 0
    storage = LocalStorageService(get_settings().upload_dir)
    for upload in files:
        content = upload.file.read()
        if len(content) > get_settings().max_upload_bytes:
            raise ApiError(ErrorCode.FILE_TOO_LARGE, "Uploaded image is too large.")
        try:
            validated = validate_image_upload(content, upload.content_type or "", upload.filename or "upload")
        except ValueError as error:
            raise ApiError(ErrorCode.INVALID_FILE_TYPE, str(error)) from error
        saved = storage.save(validated.content, validated.original_name, validated.mime_type)
        job.sources.append(
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
        position += 1
    if normalized_text:
        job.sources.append(ImportJobSource(type=SourceType.TEXT, status=ImportSourceStatus.READY, text=normalized_text, position=position))
        position += 1
    if normalized_url:
        job.sources.append(ImportJobSource(type=SourceType.URL, status=ImportSourceStatus.READY, url=normalized_url, position=position))
    session.add(job)
    session.commit()
    session.refresh(job)
    log_info(
        logger,
        "[recipes.import] Import job created",
        ownerId=owner_id,
        importJobId=job.id,
        clientId=client_id,
        clientImportId=client_import_id,
        sourceCount=len(job.sources),
        hasText=normalized_text is not None,
        hasUrl=normalized_url is not None,
        attachmentCount=len(files),
    )
    process_import_job(session, job.id)
    return session.get(ImportJob, job.id)


def process_import_job(session: Session, job_id: str) -> None:
    job = session.get(ImportJob, job_id)
    if job is None or job.status == ImportJobStatus.SUCCEEDED:
        return
    job.status = ImportJobStatus.PROCESSING
    job.started_at = datetime.now(timezone.utc)
    session.commit()
    log_info(logger, "[recipes.import] Import job processing started", ownerId=job.owner_id, importJobId=job.id)

    storage = LocalStorageService(get_settings().upload_dir)
    saved_storage_keys = [source.image_storage_key for source in job.sources if source.image_storage_key]
    source_drafts: list[SourceDraft] = []
    loaded_urls: list[str] = []
    imported_author_name: str | None = None
    for source in sorted(job.sources, key=lambda item: item.position):
        if source.type == SourceType.TEXT and source.text:
            source_drafts.append(
                SourceDraft(type=SourceType.TEXT, source=RecipeSourceOrigin.MANUAL, text=source.text, position=len(source_drafts))
            )
        elif source.type == SourceType.IMAGE and source.image_storage_key and source.mime_type:
            source_drafts.append(
                SourceDraft(
                    type=SourceType.IMAGE,
                    source=RecipeSourceOrigin.MANUAL,
                    image_storage_key=source.image_storage_key,
                    image_bytes=storage.read(source.image_storage_key),
                    mime_type=source.mime_type,
                    original_name=source.original_name or "upload",
                    position=len(source_drafts),
                )
            )
        elif source.type == SourceType.URL and source.url:
            parent_key = f"url:{source.position}"
            source_drafts.append(
                SourceDraft(
                    type=SourceType.URL,
                    source=RecipeSourceOrigin.MANUAL,
                    url=source.url,
                    key=parent_key,
                    position=len(source_drafts),
                )
            )
            image_count = len([draft for draft in source_drafts if draft.type == SourceType.IMAGE])
            remaining_images = max(0, get_settings().max_import_images - image_count)
            log_info(
                logger,
                "[recipes.import] Import image capacity",
                ownerId=job.owner_id,
                importJobId=job.id,
                acceptedAttachmentCount=image_count,
                remainingRemoteImageCount=remaining_images,
            )
            loaded_url = anyio.run(
                _url_content_loader_registry.load,
                source.url,
                remaining_images,
                get_settings().max_upload_bytes,
            )
            loaded_urls.append(loaded_url.url)
            if loaded_url.author_name and imported_author_name is None:
                imported_author_name = loaded_url.author_name
            source_drafts[-1].url = loaded_url.url
            source_drafts.append(
                SourceDraft(
                    type=SourceType.TEXT,
                    source=RecipeSourceOrigin.URL,
                    parent_key=parent_key,
                    text=loaded_url.text,
                    position=len(source_drafts),
                )
            )
            for remote_image in loaded_url.images[:remaining_images]:
                saved = storage.save(remote_image.bytes, remote_image.original_name, remote_image.mime_type)
                saved_storage_keys.append(saved.storage_key)
                source_drafts.append(
                    SourceDraft(
                        type=SourceType.IMAGE,
                        source=RecipeSourceOrigin.URL,
                        parent_key=parent_key,
                        image_storage_key=saved.storage_key,
                        image_bytes=remote_image.bytes,
                        mime_type=remote_image.mime_type,
                        original_name=remote_image.original_name,
                        position=len(source_drafts),
                    )
                )
            loaded_videos = loaded_url.videos[: get_settings().max_import_videos]
            if loaded_videos:
                started_at = datetime.now(timezone.utc)
                try:
                    first_pass_video_sources = _coerce_first_pass_video_sources(
                        anyio.run(
                            _prepare_first_pass_video_sources,
                            _video_processor(),
                            loaded_videos,
                            get_settings().max_upload_bytes,
                            get_settings().max_video_bytes,
                        )
                    )
                except Exception as error:
                    log_error(
                        logger,
                        "[recipes.import] Video first-pass processing failed",
                        ownerId=job.owner_id,
                        importJobId=job.id,
                        videoCount=len(loaded_videos),
                        error=repr(error),
                    )
                    first_pass_video_sources = FirstPassVideoSources()
                trimmed_transcript = (first_pass_video_sources.transcript_text or "").strip()
                log_info(
                    logger,
                    "[recipes.import] Video first-pass processed",
                    ownerId=job.owner_id,
                    importJobId=job.id,
                    videoCount=len(loaded_videos),
                    posterImageCount=len(first_pass_video_sources.poster_images),
                    hasTranscript=bool(trimmed_transcript),
                    transcriptCharCount=len(trimmed_transcript),
                    durationMs=int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000),
                )
                if trimmed_transcript:
                    source_drafts.append(
                        SourceDraft(
                            type=SourceType.TEXT,
                            source=RecipeSourceOrigin.URL_VIDEO,
                            parent_key=parent_key,
                            text=trimmed_transcript,
                            position=len(source_drafts),
                        )
                    )
                for poster in first_pass_video_sources.poster_images:
                    image_count = len([draft for draft in source_drafts if draft.type == SourceType.IMAGE])
                    if image_count >= get_settings().max_import_images:
                        break
                    saved = storage.save(poster.bytes, poster.original_name, poster.mime_type)
                    saved_storage_keys.append(saved.storage_key)
                    source_drafts.append(
                        SourceDraft(
                            type=SourceType.IMAGE,
                            source=RecipeSourceOrigin.URL_VIDEO,
                            parent_key=parent_key,
                            image_storage_key=saved.storage_key,
                            image_bytes=poster.bytes,
                            mime_type=poster.mime_type,
                            original_name=poster.original_name,
                            position=len(source_drafts),
                        )
                    )

    source_name_result = derive_source_name(loaded_urls)
    if not source_name_result.ok:
        _cleanup_storage_keys(storage, saved_storage_keys)
        job.status = ImportJobStatus.FAILED
        job.error_code = source_name_result.error_code
        job.error_message = "URL sources include mixed platforms."
        job.finished_at = datetime.now(timezone.utc)
        session.commit()
        log_info(
            logger,
            "[recipes.import] Import job failed",
            ownerId=job.owner_id,
            importJobId=job.id,
            errorCode=job.error_code,
            errorMessage=job.error_message,
        )
        return

    recipe = Recipe(
        owner_id=job.owner_id,
        title="Import pending",
        instructions=[],
        source_name=source_name_result.source_name,
    )
    recipe_sources: list[RecipeSource] = []
    image_by_source: dict[RecipeSource, RecipeImage] = {}
    source_by_key: dict[str, RecipeSource] = {}
    for draft in source_drafts:
        image: RecipeImage | None = None
        if draft.type == SourceType.IMAGE and draft.image_storage_key and draft.mime_type and draft.original_name:
            image = RecipeImage(
                role=RecipeImageRole.SOURCE,
                storage_key=draft.image_storage_key,
                original_name=draft.original_name,
                mime_type=draft.mime_type,
                size_bytes=len(draft.image_bytes or b""),
                position=draft.position,
            )
            recipe.images.append(image)
        recipe_source = RecipeSource(
            owner_id=job.owner_id,
            type=draft.type,
            source=draft.source,
            parent=source_by_key.get(draft.parent_key) if draft.parent_key else None,
            url=draft.url,
            text=draft.text,
            image=image,
            position=draft.position,
            status=RecipeSourceStatus.UNKNOWN,
        )
        recipe.sources.append(recipe_source)
        recipe_sources.append(recipe_source)
        if image is not None:
            image_by_source[recipe_source] = image
        if draft.key:
            source_by_key[draft.key] = recipe_source
    final_sources = [source for source in recipe_sources if source.type != SourceType.URL]
    ai_id_by_source = {source: f"source_{index}" for index, source in enumerate(final_sources, start=1)}
    ready_sources = [
        ReadySource(
            id=ai_id_by_source[source],
            type=source.type.value,
            storageKey=source.image.storage_key if source.image else None,
            dataUrl=image_to_data_url(storage.read(source.image.storage_key), source.image.mime_type) if source.image else None,
            mimeType=source.image.mime_type if source.image else None,
            originalName=source.image.original_name if source.image else None,
            text=source.text,
            position=source.position or 0,
        )
        for source in final_sources
    ]
    started_at = datetime.now(timezone.utc)
    provider_name, provider = _recipe_extraction_provider()
    log_info(
        logger,
        "[recipes.import] AI provider selected",
        ownerId=job.owner_id,
        importJobId=job.id,
        provider=provider_name,
    )
    try:
        result = anyio.run(provider.extract, ready_sources)
    except Exception as error:
        log_error(
            logger,
            "[recipes.import] AI extraction provider threw",
            ownerId=job.owner_id,
            importJobId=job.id,
            sourceCount=len(ready_sources),
            error=repr(error),
        )
        _cleanup_storage_keys(storage, saved_storage_keys)
        job.status = ImportJobStatus.FAILED
        job.error_code = ErrorCode.AI_UNAVAILABLE.value
        job.error_message = "AI extraction is unavailable."
        job.finished_at = datetime.now(timezone.utc)
        session.commit()
        return
    log_info(
        logger,
        "[recipes.import] Import step timing",
        ownerId=job.owner_id,
        importJobId=job.id,
        step="ai_extraction",
        durationMs=int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000),
    )
    if result.not_a_recipe or result.recipe is None:
        _cleanup_storage_keys(storage, saved_storage_keys)
        job.status = ImportJobStatus.FAILED
        job.error_code = ErrorCode.NOT_A_RECIPE.value
        job.error_message = "The provided sources do not contain a recipe."
        job.finished_at = datetime.now(timezone.utc)
        session.commit()
        log_info(
            logger,
            "[recipes.import] Import job failed",
            ownerId=job.owner_id,
            importJobId=job.id,
            errorCode=job.error_code,
            errorMessage=job.error_message,
        )
        return

    recipe_result = result.recipe
    is_single_url_import = len(job.sources) == 1 and job.sources[0].type == SourceType.URL
    status_quality = normalize_quality_source_refs(recipe_result.quality, ready_sources)
    recipe_quality = normalize_single_url_quality(status_quality, is_single_url_import)
    recipe_result = recipe_result.model_copy(update={"quality": recipe_quality})
    if recipe_result.quality.confidence <= get_settings().import_min_confidence:
        _cleanup_storage_keys(storage, saved_storage_keys)
        job.status = ImportJobStatus.FAILED
        job.error_code = ErrorCode.NOT_A_RECIPE.value
        job.error_message = "The extracted recipe confidence is too low."
        job.finished_at = datetime.now(timezone.utc)
        session.commit()
        log_info(
            logger,
            "[recipes.import] Import job failed",
            ownerId=job.owner_id,
            importJobId=job.id,
            errorCode=job.error_code,
            errorMessage=job.error_message,
            confidence=recipe_result.quality.confidence,
        )
        return
    log_info(
        logger,
        "[recipes.import] AI extraction quality",
        ownerId=job.owner_id,
        importJobId=job.id,
        confidence=recipe_result.quality.confidence,
        hasConflicts=recipe_result.quality.hasConflicts,
        hasIgnored=recipe_result.quality.hasIgnored,
        primarySourceRefs=recipe_result.quality.primarySourceRefs,
        ignoredSourceRefs=recipe_result.quality.ignoredSourceRefs,
    )
    recipe.title = recipe_result.title
    recipe.instructions = recipe_result.instructions
    recipe.servings = recipe_result.servings
    recipe.cook_time_minutes = recipe_result.cookTimeMinutes
    recipe.nutrition_estimate = recipe_result.nutritionEstimate.model_dump() if recipe_result.nutritionEstimate else None
    recipe.author_name = recipe_result.authorName or imported_author_name
    for index, ingredient in enumerate(recipe_result.ingredients):
        recipe.ingredients.append(
            Ingredient(
                name=ingredient.name,
                quantity=ingredient.quantity,
                unit=ingredient.unit,
                note=ingredient.note,
                position=index,
            )
        )
    image_by_ref: dict[str, RecipeImage] = {
        ai_id_by_source[source]: source.image for source in final_sources if source.image is not None
    }
    cover_image: RecipeImage | None = None
    candidate_ref = _cover_candidate_ref(
        recipe_result.coverCandidate.sourceRef if recipe_result.coverCandidate else None,
        set(image_by_ref.keys()),
    )
    if candidate_ref is not None and recipe_result.coverCandidate is not None:
        chosen = anyio.run(
            choose_cover_candidate,
            CoverGuardInput(
                candidate=ImportCoverCandidate(sourceRef=candidate_ref, crop=recipe_result.coverCandidate.crop),
                acceptedImageRefs=list(image_by_ref.keys()),
                fallbackCandidates=[],
                enabled=get_settings().enable_cover_candidate_guard,
                maxFallbackCandidates=get_settings().max_cover_fallback_candidates,
            ),
            None,
        )
        if chosen is not None:
            source_image = image_by_ref[chosen.sourceRef]
            cover_file = create_cover_image(storage, source_image.storage_key, chosen.crop, auto_crop_full_image=True)
            saved_storage_keys.append(cover_file.storage_key)
            cover_image = RecipeImage(
                role=RecipeImageRole.COVER,
                source_image=source_image,
                storage_key=cover_file.storage_key,
                original_name=cover_file.original_name,
                mime_type=cover_file.mime_type,
                size_bytes=cover_file.size_bytes,
                position=0,
            )
            recipe.cover_image_source = CoverImageSource.AI
            recipe.images.append(cover_image)
            log_info(
                logger,
                "[recipes.import] Cover image generated",
                ownerId=job.owner_id,
                importJobId=job.id,
                sourceRef=chosen.sourceRef,
                storageKey=cover_file.storage_key,
            )
    has_ignored_primary = _apply_source_statuses(recipe_sources, final_sources, status_quality, ai_id_by_source)
    warn_confidence = get_settings().import_warn_confidence
    reasons = review_reason_codes(recipe_result.quality, warn_confidence, has_ignored_primary)
    if should_create_primary_review_flag(recipe_result.quality, warn_confidence, has_ignored_primary):
        recipe.review_flags.append(
            RecipeReviewFlag(
                owner_id=job.owner_id,
                type=RecipeReviewFlagType.CONTENT_WARNING,
                status=RecipeReviewFlagStatus.OPEN,
                reason_code=reasons[0],
                message=f"Review suggested: {', '.join(reasons)}.",
                details={**recipe_result.quality.model_dump(), "reasons": reasons},
            )
        )
        log_info(
            logger,
            "[recipes.import] Recipe review flag created",
            ownerId=job.owner_id,
            importJobId=job.id,
            reasonCodes=reasons,
            confidence=recipe_result.quality.confidence,
            hasConflicts=recipe_result.quality.hasConflicts,
            hasIgnored=recipe_result.quality.hasIgnored,
        )
    session.add(recipe)
    session.flush()
    if cover_image is not None:
        recipe.cover_image_id = cover_image.id
    job.created_recipe_id = recipe.id
    job.status = ImportJobStatus.SUCCEEDED
    job.finished_at = datetime.now(timezone.utc)
    session.commit()
    log_info(
        logger,
        "[recipes.import] Import job succeeded",
        ownerId=job.owner_id,
        importJobId=job.id,
        recipeId=recipe.id,
        readySourceCount=len(ready_sources),
    )


def get_import_job(session: Session, job_id: str, owner_id: str) -> ImportJob:
    job = session.scalar(select(ImportJob).where(ImportJob.id == job_id, ImportJob.owner_id == owner_id))
    if job is None:
        raise ApiError(ErrorCode.IMPORT_NOT_FOUND, "Import job not found.", status_code=404)
    return job
