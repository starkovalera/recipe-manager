from typing import Protocol

from app.imports.source_loading.url_loaders.types import LoadedUrlContent


class UrlContentService(Protocol):
    async def load(self, url: str, max_images: int, max_image_bytes: int) -> LoadedUrlContent: ...
