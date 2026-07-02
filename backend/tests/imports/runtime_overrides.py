from app.ai.provider import RecipeExtractionProvider
from app.imports import runtime
from app.imports.runtime import UrlContentRegistry


def set_url_content_loader_registry(registry: UrlContentRegistry) -> None:
    runtime._url_content_loader_registry_override = registry


def reset_url_content_loader_registry() -> None:
    runtime._url_content_loader_registry_override = None


def set_recipe_extraction_provider(provider: RecipeExtractionProvider) -> None:
    runtime._recipe_extraction_provider_override = provider


def reset_recipe_extraction_provider() -> None:
    runtime._recipe_extraction_provider_override = None


def set_video_processor(processor) -> None:
    runtime._video_processor_override = processor


def reset_video_processor() -> None:
    runtime._video_processor_override = None
