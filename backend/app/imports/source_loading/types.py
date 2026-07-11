from typing import Protocol

from app.imports.source_loading.results import (
    SecondaryResourceKind,
    SecondaryResourceLoadResult,
    SecondaryResourceLoadStatus,
)
from app.imports.source_loading.url_loaders.types import LoadedUrlContent

__all__ = [
    "SecondaryResourceKind",
    "SecondaryResourceLoadResult",
    "SecondaryResourceLoadStatus",
    "UrlContentService",
]


class UrlContentService(Protocol):
    async def load(self, url: str, max_images: int, max_image_bytes: int) -> LoadedUrlContent: ...
