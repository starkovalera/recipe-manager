from app.imports.recipe_builder import RawSource, build_ready_sources, build_recipe_from_raw_sources
from app.models import RecipeResourceOrigin, SourceType


class MemoryStorage:
    def __init__(self, files: dict[str, bytes]):
        self.files = files

    def read(self, storage_key: str) -> bytes:
        return self.files[storage_key]


def test_build_recipe_from_raw_sources_preserves_url_parent_child_tree():
    recipe, resources, final_resources, ai_id_by_resource = build_recipe_from_raw_sources(
        owner_id="user-1",
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
    )

    assert recipe.owner_id == "user-1"
    assert len(resources) == 2
    assert resources[1].parent is resources[0]
    assert final_resources == [resources[1]]
    assert ai_id_by_resource == {resources[1]: "source_1"}


def test_build_ready_sources_sends_final_sources_only_with_short_ai_ids():
    recipe, _resources, final_resources, ai_id_by_resource = build_recipe_from_raw_sources(
        owner_id="user-1",
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
    )

    ready_sources = build_ready_sources(final_resources, ai_id_by_resource, MemoryStorage({"images/source.jpg": b"image-bytes"}))

    assert len(recipe.images) == 1
    assert [(source.id, source.type, source.originalName, source.text) for source in ready_sources] == [
        ("source_1", "IMAGE", "source.jpg", None),
        ("source_2", "TEXT", None, "Manual text"),
    ]
    assert ready_sources[0].dataUrl.startswith("data:image/jpeg;base64,")
