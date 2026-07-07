from app.imports.config import ImportConfig
from app.imports.job_stages import extraction_sources as extraction_sources_module
from app.imports.job_stages.extraction_sources import build_extraction_context
from app.imports.job_stages.raw_recipe import build_raw_recipe
from app.imports.job_stages.raw_sources import RawSource, build_raw_sources
from app.models import ImportJob, ImportJobSource, RecipeResourceOrigin, SourceType, Tag


class MemoryStorage:
    def __init__(self, files: dict[str, bytes]):
        self.files = files

    def read(self, storage_key: str) -> bytes:
        return self.files[storage_key]


class EmptyUrlContentService:
    async def load(self, url: str, max_images: int, max_image_bytes: int):
        raise AssertionError("URL loader should not be called")


class EmptyVideoProcessor:
    async def prepare_first_pass_video_sources(self, *, videos, max_image_bytes: int, max_video_bytes: int):
        raise AssertionError("Video processor should not be called")


def test_build_raw_sources_preserves_manual_text_and_image_order():
    job = ImportJob(owner_id="user-1", client_id="client-1")
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

    raw_sources, imported_author_name = build_raw_sources(
        job,
        MemoryStorage({"images/source.jpg": b"image-bytes"}),
        saved_storage_keys=[],
        url_content_loader=EmptyUrlContentService(),
        video_processor=EmptyVideoProcessor(),
        import_config=ImportConfig(max_import_images=5, max_upload_bytes=1000, max_import_videos=1, max_video_bytes=1000),
    )

    assert imported_author_name is None
    assert [(source.type, source.source, source.position) for source in raw_sources] == [
        (SourceType.IMAGE, RecipeResourceOrigin.MANUAL, 0),
        (SourceType.TEXT, RecipeResourceOrigin.MANUAL, 1),
    ]
    assert raw_sources[0].image_bytes == b"image-bytes"
    assert raw_sources[0].original_name == "source.jpg"
    assert raw_sources[1].text == "Manual text"


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

    context = build_extraction_context(
        content_recipe_resources=content_resources,
        job=ImportJob(owner_id="user-1"),
        session=None,
        storage=MemoryStorage({"images/source.jpg": b"image-bytes"}),
    )

    assert len(recipe.images) == 1
    assert context.tags == tags
    assert [(source.id, source.type, source.original_name, source.text) for source in context.extraction_sources] == [
        ("source_1", "IMAGE", "source.jpg", None),
        ("source_2", "TEXT", None, "Manual text"),
    ]
    assert context.extraction_sources[0].data_url.startswith("data:image/jpeg;base64,")
    assert context.extraction_id_by_resource == {
        content_resources[0]: "source_1",
        content_resources[1]: "source_2",
    }
