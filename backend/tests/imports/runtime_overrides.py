from app.ai.provider import RecipeExtractionProvider
from app.imports import runtime
from app.imports.source_loading.types import UrlContentService


def set_url_content_service(service: UrlContentService) -> None:
    runtime._url_content_service_override = service


def reset_url_content_service() -> None:
    runtime._url_content_service_override = None


def set_recipe_extraction_provider(provider: RecipeExtractionProvider) -> None:
    runtime._recipe_extraction_provider_override = provider


def reset_recipe_extraction_provider() -> None:
    runtime._recipe_extraction_provider_override = None


def set_video_processor(processor) -> None:
    runtime._video_processor_override = processor


def reset_video_processor() -> None:
    runtime._video_processor_override = None
