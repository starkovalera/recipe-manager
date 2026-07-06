from app.ai.factory import create_recipe_extraction_provider
from app.ai.provider import RecipeExtractionProvider
from app.core.config import get_settings
from app.imports.source_loading.types import UrlContentService
from app.imports.source_loading.url_loaders.generic import GenericUrlContentLoader
from app.imports.source_loading.url_loaders.instagram import InstagramUrlContentLoader
from app.imports.source_loading.url_loaders.registry import UrlContentLoaderRegistry
from app.imports.source_loading.url_loaders.threads import ThreadsUrlContentLoader
from app.imports.source_loading.url_loaders.types import LoadedUrlContent
from app.imports.source_loading.video_processors.generic import VideoProcessor


class DefaultUrlContentService:
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


_url_content_service_override: UrlContentService | None = None
_recipe_extraction_provider_override: RecipeExtractionProvider | None = None
_video_processor_override = None


def get_url_content_service() -> UrlContentService:
    return _url_content_service_override or DefaultUrlContentService()


def get_recipe_extraction_provider() -> tuple[str, RecipeExtractionProvider]:
    if _recipe_extraction_provider_override is not None:
        return "test", _recipe_extraction_provider_override
    return create_recipe_extraction_provider(get_settings())


def get_video_processor():
    return _video_processor_override or VideoProcessor(get_settings())
