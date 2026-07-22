from contextlib import contextmanager

import pytest

from app.ai.schemas import (
    ExtractedIngredient,
    ExtractedRecipe,
    ExtractionQuality,
    ExtractionResult,
    ExtractionSource,
)
from app.imports.config import ImportConfig
from app.imports.error_codes import (
    ExtractorUnavailableError,
    ImportExtractionErrorCode,
    InvalidExtractionResult,
    NotARecipeError,
    ResultParseError,
    SecondaryResourceUploadError,
)
from app.imports.job_context import ImportJobContext
from app.imports.job_stages import extraction_sources as extraction_sources_module
from app.imports.job_stages.extraction import extract, validate_extraction_result
from app.imports.job_stages.extraction_sources import ExtractionContext, build_extraction_context
from app.imports.job_stages.raw_recipe import build_raw_recipe
from app.imports.job_stages.raw_sources import RawSource, build_raw_sources
from app.imports.source_loading.results import (
    SecondaryResourceKind,
    SecondaryResourceLoadResult,
    SecondaryResourceLoadStatus,
)
from app.imports.source_loading.url_loaders.types import LoadedRemoteImage, LoadedRemoteVideo, LoadedUrlContent
from app.imports.source_loading.video_processors.types import FirstPassVideoSources
from app.models import (
    ImportJob,
    ImportJobSource,
    ImportJobStatus,
    RecipeResourceOrigin,
    SourceType,
    Tag,
)
from app.storage.constants import StorageLocation, StoragePurpose
from app.storage.types import StorageWriteContext, StoredFile


class MemoryStorage:
    def __init__(self, files: dict[str, bytes]):
        self.files = files
        self.saved: list[tuple[StorageLocation, StorageWriteContext, str]] = []

    def read(self, location: StorageLocation, storage_key: str) -> bytes:
        assert location is StorageLocation.USER_MEDIA
        return self.files[storage_key]

    def save(
        self,
        location: StorageLocation,
        content: bytes,
        original_name: str,
        mime_type: str,
        *,
        context: StorageWriteContext,
    ) -> StoredFile:
        assert location is StorageLocation.USER_MEDIA
        assert context.purpose is StoragePurpose.IMPORT_DERIVED
        stored = StoredFile(
            storage_key=f"secondary/{original_name}",
            original_name=original_name,
            mime_type=mime_type,
            size_bytes=len(content),
        )
        self.saved.append((location, context, stored.storage_key))
        self.files[stored.storage_key] = content
        return stored


class EmptyUrlContentService:
    async def load(self, url: str, max_images: int, max_image_bytes: int):
        raise AssertionError("URL loader should not be called")


class EmptyVideoProcessor:
    async def prepare_first_pass_video_sources(self, *, videos, max_image_bytes: int, max_video_bytes: int):
        raise AssertionError("Video processor should not be called")


class StaticUrlContentService:
    def __init__(self, content: LoadedUrlContent | None = None, error: Exception | None = None):
        self.content = content
        self.error = error

    async def load(self, url: str, max_images: int, max_image_bytes: int):
        if self.error is not None:
            raise self.error
        return self.content


class StaticVideoProcessor:
    def __init__(self, result: FirstPassVideoSources):
        self.result = result

    async def prepare_first_pass_video_sources(self, *, videos, max_image_bytes: int, max_video_bytes: int):
        return self.result


class RecipeExtractionProvider:
    def __init__(self, result: ExtractionResult | None = None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls: list[dict] = []

    async def extract(self, sources, *, language: str, tags: str):
        self.calls.append({"sources": sources, "language": language, "tags": tags})
        if self.error is not None:
            raise self.error
        return self.result


def import_config() -> ImportConfig:
    return ImportConfig(
        max_import_images=5,
        max_upload_bytes=1000,
        max_import_videos=1,
        max_video_bytes=1000,
        max_recipe_ingredients=50,
        max_recipe_instruction_chars=1000,
        import_min_confidence=0.2,
        import_warn_confidence=0.75,
    )


def extracted_recipe() -> ExtractedRecipe:
    return ExtractedRecipe(
        title="Recipe",
        ingredients=[ExtractedIngredient(name="Ingredient")],
        instructions=["Cook."],
        quality=ExtractionQuality(
            confidence=0.9,
            has_conflicts=False,
            has_ignored=False,
            primary_source_refs=["source_1"],
            ignored_source_refs=[],
        ),
    )


def extraction_context() -> ExtractionContext:
    return ExtractionContext(
        extraction_sources=[ExtractionSource(id="source_1", type="TEXT", position=0, text="Recipe text")],
        extraction_id_by_resource={},
        tag_names=["quick", "dinner"],
        language="ru",
    )


def import_job() -> ImportJob:
    return ImportJob(id="job-1", owner_id="user-1", client_id="client-1", status=ImportJobStatus.RUNNING)


def import_job_context() -> ImportJobContext:
    return ImportJobContext.from_job(import_job())


def test_build_raw_sources_preserves_manual_text_and_image_order():
    job = import_job()
    job.sources = [
        ImportJobSource(
            type=SourceType.IMAGE,
            image_storage_key="images/source.jpg",
            original_name="source.jpg",
            mime_type="image/jpeg",
            position=0,
        ),
        ImportJobSource(type=SourceType.TEXT, text="Manual text", position=1),
    ]

    result = build_raw_sources(
        job,
        MemoryStorage({"images/source.jpg": b"image-bytes"}),
        secondary_storage_keys=[],
        url_content_loader=EmptyUrlContentService(),
        video_processor=EmptyVideoProcessor(),
        import_config=import_config(),
    )

    assert result.imported_author_name is None
    assert result.secondary_resource_results == []
    assert [(source.type, source.source, source.position) for source in result.raw_sources] == [
        (SourceType.IMAGE, RecipeResourceOrigin.MANUAL, 0),
        (SourceType.TEXT, RecipeResourceOrigin.MANUAL, 1),
    ]
    assert result.raw_sources[0].image_bytes == b"image-bytes"
    assert result.raw_sources[0].original_name == "source.jpg"
    assert result.raw_sources[1].text == "Manual text"


def test_build_raw_sources_keeps_partial_url_content_and_reports_failed_transcript():
    job = import_job()
    job.sources = [ImportJobSource(type=SourceType.URL, url="https://example.com/post", position=0)]
    video = LoadedRemoteVideo(
        url="https://cdn.example/video.mp4",
        poster_url="https://cdn.example/poster.jpg",
        position=0,
        original_name="video.mp4",
    )
    transcript_failure = SecondaryResourceLoadResult(
        kind=SecondaryResourceKind.VIDEO_TRANSCRIPT,
        status=SecondaryResourceLoadStatus.FAILED,
        position=0,
        url=video.url,
        original_name=video.original_name,
        error="RuntimeError('transcription failed')",
    )

    storage = MemoryStorage({})
    secondary_storage_keys: list[str] = []
    result = build_raw_sources(
        job,
        storage,
        secondary_storage_keys=secondary_storage_keys,
        url_content_loader=StaticUrlContentService(
            LoadedUrlContent(
                url="https://example.com/post",
                text="Recipe caption",
                videos=[video],
            )
        ),
        video_processor=StaticVideoProcessor(
            FirstPassVideoSources(
                poster_images=[
                    LoadedRemoteImage(
                        bytes=b"poster",
                        mime_type="image/jpeg",
                        original_name="poster-video.jpg",
                        url=video.poster_url or "",
                        position=0,
                    )
                ],
                resource_results=[transcript_failure],
            )
        ),
        import_config=import_config(),
    )

    assert [(source.type, source.source) for source in result.raw_sources] == [
        (SourceType.URL, RecipeResourceOrigin.MANUAL),
        (SourceType.TEXT, RecipeResourceOrigin.URL),
        (SourceType.IMAGE, RecipeResourceOrigin.URL_VIDEO),
    ]
    assert transcript_failure in result.secondary_resource_results
    assert secondary_storage_keys == ["secondary/poster-video.jpg"]
    assert storage.saved == [
        (
            StorageLocation.USER_MEDIA,
            StorageWriteContext(
                owner_id="user-1",
                purpose=StoragePurpose.IMPORT_DERIVED,
                entity_id="job-1",
            ),
            "secondary/poster-video.jpg",
        )
    ]


def test_build_raw_sources_rejects_sole_url_with_only_video_posters():
    job = import_job()
    job.sources = [ImportJobSource(type=SourceType.URL, url="https://example.com/post", position=0)]
    video = LoadedRemoteVideo(
        url="https://cdn.example/video.mp4",
        poster_url="https://cdn.example/poster.jpg",
        position=0,
        original_name="video.mp4",
    )

    with pytest.raises(SecondaryResourceUploadError):
        build_raw_sources(
            job,
            MemoryStorage({}),
            secondary_storage_keys=[],
            url_content_loader=StaticUrlContentService(LoadedUrlContent(url="https://example.com/post", text=None, videos=[video])),
            video_processor=StaticVideoProcessor(
                FirstPassVideoSources(
                    poster_images=[
                        LoadedRemoteImage(
                            bytes=b"poster",
                            mime_type="image/jpeg",
                            original_name="poster-video.jpg",
                            url=video.poster_url or "",
                            position=0,
                        )
                    ]
                )
            ),
            import_config=import_config(),
        )


def test_build_raw_sources_keeps_manual_evidence_when_url_content_loading_fails():
    job = import_job()
    job.sources = [
        ImportJobSource(type=SourceType.TEXT, text="Manual recipe", position=0),
        ImportJobSource(type=SourceType.URL, url="https://example.com/post", position=1),
    ]

    result = build_raw_sources(
        job,
        MemoryStorage({}),
        secondary_storage_keys=[],
        url_content_loader=StaticUrlContentService(error=RuntimeError("page unavailable")),
        video_processor=EmptyVideoProcessor(),
        import_config=import_config(),
    )

    assert [source.type for source in result.raw_sources] == [SourceType.TEXT, SourceType.URL]
    assert len(result.failed_secondary_resources) == 1
    assert result.failed_secondary_resources[0].kind == SecondaryResourceKind.URL_CONTENT


def test_build_raw_recipe_preserves_url_parent_child_tree():
    recipe, resources, content_resources = build_raw_recipe(
        raw_sources=[
            RawSource(type=SourceType.URL, source=RecipeResourceOrigin.MANUAL, key="url:0", url="https://example.com", position=0),
            RawSource(
                type=SourceType.TEXT,
                source=RecipeResourceOrigin.URL,
                parent_key="url:0",
                text="URL recipe text",
                position=1,
            ),
        ],
        owner_id="user-1",
        imported_author_name="url_author",
    )

    assert recipe.owner_id == "user-1"
    assert recipe.author_name == "url_author"
    assert len(resources) == 2
    assert resources[1].parent is resources[0]
    assert content_resources == [resources[1]]


def test_build_extraction_context_sends_content_resources_only_with_short_ai_ids(monkeypatch):
    recipe, _resources, content_resources = build_raw_recipe(
        raw_sources=[
            RawSource(
                type=SourceType.IMAGE,
                source=RecipeResourceOrigin.MANUAL,
                image_storage_key="images/source.jpg",
                image_bytes=b"image-bytes",
                mime_type="image/jpeg",
                original_name="source.jpg",
                position=0,
            ),
            RawSource(type=SourceType.TEXT, source=RecipeResourceOrigin.MANUAL, text="Manual text", position=1),
        ],
        owner_id="user-1",
    )
    tags = [Tag(name="quick")]
    monkeypatch.setattr(extraction_sources_module, "list_active_tags", lambda _session, owner_id: tags)

    @contextmanager
    def fake_db_session():
        yield None

    monkeypatch.setattr(extraction_sources_module, "db_session", fake_db_session)

    context = build_extraction_context(
        content_recipe_resources=content_resources,
        job_context=ImportJobContext.from_job(ImportJob(owner_id="user-1")),
        storage=MemoryStorage({"images/source.jpg": b"image-bytes"}),
    )

    assert len(recipe.images) == 1
    assert context.tag_names == ["quick"]
    assert [(source.id, source.type, source.original_name, source.text) for source in context.extraction_sources] == [
        ("source_1", "IMAGE", "source.jpg", None),
        ("source_2", "TEXT", None, "Manual text"),
    ]
    assert context.extraction_sources[0].data_url.startswith("data:image/jpeg;base64,")
    assert context.extraction_id_by_resource == {
        content_resources[0]: "source_1",
        content_resources[1]: "source_2",
    }


def test_extract_calls_provider_without_recording_extractor_events():
    provider = RecipeExtractionProvider(ExtractionResult(recipe=extracted_recipe()))
    job_context = import_job_context()
    context = extraction_context()

    result = extract(job_context, context, "test-provider", provider)

    assert result.recipe is not None
    assert result.recipe.title == "Recipe"
    assert provider.calls == [
        {
            "sources": context.extraction_sources,
            "language": "ru",
            "tags": "quick, dinner",
        }
    ]
    assert job_context.to_dict()["id"] == "job-1"


def test_extract_maps_provider_exception_to_extractor_unavailable():
    provider = RecipeExtractionProvider(error=RuntimeError("provider down"))

    with pytest.raises(ExtractorUnavailableError) as exc_info:
        extract(import_job_context(), extraction_context(), "test-provider", provider)

    assert exc_info.value.code == ImportExtractionErrorCode.EXTRACTOR_UNAVAILABLE
    assert exc_info.value.extra == {"original_error": "provider down"}


@pytest.mark.parametrize(
    ("error_code", "expected_error"),
    [
        (ImportExtractionErrorCode.RESULT_PARSE_FAILED, ResultParseError),
        (ImportExtractionErrorCode.INVALID_EXTRACTION_RESULT, InvalidExtractionResult),
        (ImportExtractionErrorCode.EXTRACTOR_UNAVAILABLE, ExtractorUnavailableError),
        (ImportExtractionErrorCode.NOT_A_RECIPE, NotARecipeError),
        (None, NotARecipeError),
    ],
)
def test_validate_extraction_result_maps_invalid_provider_result_to_import_extraction_error(error_code, expected_error):
    with pytest.raises(expected_error) as exc_info:
        validate_extraction_result(
            ExtractionResult(
                not_a_recipe=True,
                error_code=error_code,
                error_message="provider message",
            )
        )

    assert exc_info.value.extra == {"provider_message": "provider message"}
