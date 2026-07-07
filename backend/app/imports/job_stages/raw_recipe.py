from app.imports.job_stages.raw_sources import RawSource
from app.models import Recipe, RecipeImage, RecipeResource, RecipeResourceRole, RecipeResourceStatus, SourceType


def build_raw_recipe(
        raw_sources: list[RawSource],
        owner_id: str,
        imported_author_name: str | None = None
) -> tuple[Recipe, list[RecipeResource], list[RecipeResource]]:
    recipe = Recipe(
        owner_id=owner_id,
        title="Import pending",
        instructions=[],
        author_name=imported_author_name,
    )
    # all preliminary recipe resources, including container-like (url) that serves as a container for another
    # resources and not associated with any real content
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

    # preliminary recipe resources associated with a real content (text, images, etc.)
    content_recipe_resources = [resource for resource in recipe_resources if resource.type != SourceType.URL]
    return recipe, recipe_resources, content_recipe_resources

