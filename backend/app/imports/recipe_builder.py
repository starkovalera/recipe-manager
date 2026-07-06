from dataclasses import dataclass
from typing import Protocol

from app.ai.schemas import ReadySource
from app.media.images import image_to_data_url
from app.models import Recipe, RecipeImage, RecipeResource, RecipeResourceOrigin, RecipeResourceRole, RecipeResourceStatus, SourceType


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
class BuiltRecipeSources:
    recipe: Recipe
    recipe_resources: list[RecipeResource]
    final_resources: list[RecipeResource]
    ai_id_by_resource: dict[RecipeResource, str]

    def __iter__(self):
        yield self.recipe
        yield self.recipe_resources
        yield self.final_resources
        yield self.ai_id_by_resource


class StorageReader(Protocol):
    def read(self, storage_key: str) -> bytes: ...


def build_recipe_from_raw_sources(owner_id: str, raw_sources: list[RawSource]) -> BuiltRecipeSources:
    recipe = Recipe(
        owner_id=owner_id,
        title="Import pending",
        instructions=[],
    )
    recipe_resources: list[RecipeResource] = []
    resource_by_key: dict[str, RecipeResource] = {}

    for raw_source in raw_sources:
        image: RecipeImage | None = None
        if raw_source.type == SourceType.IMAGE and raw_source.image_storage_key and raw_source.mime_type and raw_source.original_name:
            image = RecipeImage(
                storage_key=raw_source.image_storage_key,
                original_name=raw_source.original_name,
                mime_type=raw_source.mime_type,
                size_bytes=len(raw_source.image_bytes or b""),
                position=raw_source.position,
            )
            recipe.images.append(image)

        recipe_resource = RecipeResource(
            owner_id=owner_id,
            type=raw_source.type,
            source=raw_source.source,
            role=RecipeResourceRole.SOURCE,
            parent=resource_by_key.get(raw_source.parent_key) if raw_source.parent_key else None,
            url=raw_source.url,
            text=raw_source.text,
            image=image,
            position=raw_source.position,
            status=RecipeResourceStatus.UNKNOWN,
        )
        recipe.resources.append(recipe_resource)
        recipe_resources.append(recipe_resource)
        if raw_source.key:
            resource_by_key[raw_source.key] = recipe_resource

    final_resources = [resource for resource in recipe_resources if resource.type != SourceType.URL]
    ai_id_by_resource = {resource: f"source_{index}" for index, resource in enumerate(final_resources, start=1)}
    return BuiltRecipeSources(recipe, recipe_resources, final_resources, ai_id_by_resource)


def build_ready_sources(
    final_resources: list[RecipeResource],
    ai_id_by_resource: dict[RecipeResource, str],
    storage: StorageReader,
) -> list[ReadySource]:
    return [
        ReadySource(
            id=ai_id_by_resource[resource],
            type=resource.type.value,
            storageKey=resource.image.storage_key if resource.image else None,
            dataUrl=image_to_data_url(storage.read(resource.image.storage_key), resource.image.mime_type) if resource.image else None,
            mimeType=resource.image.mime_type if resource.image else None,
            originalName=resource.image.original_name if resource.image else None,
            text=resource.text,
            position=resource.position or 0,
        )
        for resource in final_resources
    ]
