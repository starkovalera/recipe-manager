from dataclasses import dataclass

from app.ai.schemas import ExtractionSource
from app.db.session import db_session
from app.imports.job_context import ImportJobContext
from app.media.images import image_to_data_url
from app.models import RecipeResource
from app.storage.base import StorageService
from app.tags.queries import list_active_tags


@dataclass
class ExtractionContext:
    extraction_sources: list[ExtractionSource]
    extraction_id_by_resource: dict[RecipeResource, str]
    tag_names: list[str]
    language: str


def _build_extraction_sources(
    content_recipe_resources: list[RecipeResource],
    extraction_id_by_resource: dict[RecipeResource, str],
    storage: StorageService,
) -> list[ExtractionSource]:
    return [
        ExtractionSource(
            id=extraction_id_by_resource[resource],
            type=resource.type.value,
            storage_key=resource.image.storage_key if resource.image else None,
            data_url=image_to_data_url(
                storage.read(resource.image.storage_key),
                resource.image.mime_type,
            )
            if resource.image
            else None,
            mime_type=resource.image.mime_type if resource.image else None,
            original_name=resource.image.original_name if resource.image else None,
            text=resource.text,
            position=resource.position or 0,
        )
        for resource in content_recipe_resources
    ]


def build_extraction_context(
    content_recipe_resources: list[RecipeResource],
    job_context: ImportJobContext,
    storage: StorageService,
) -> ExtractionContext:
    with db_session() as session:
        active_tags = list_active_tags(session, job_context.owner_id)
        tag_names = [tag.name for tag in active_tags]

    extraction_id_by_resource = {
        resource: f"source_{index}"
        for index, resource in enumerate(content_recipe_resources, start=1)
    }
    return ExtractionContext(
        extraction_sources=_build_extraction_sources(
            content_recipe_resources,
            extraction_id_by_resource,
            storage,
        ),
        extraction_id_by_resource=extraction_id_by_resource,
        tag_names=tag_names,
        language=job_context.recipe_language,
    )
