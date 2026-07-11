from dataclasses import dataclass, field
from typing import Protocol

from app.imports.source_loading.types import SecondaryResourceLoadResult
from app.imports.source_loading.url_loaders.types import LoadedRemoteImage


@dataclass(frozen=True)
class FirstPassVideoSources:
    poster_images: list[LoadedRemoteImage] = field(default_factory=list)
    transcript_text: str | None = None
    resource_results: list[SecondaryResourceLoadResult] = field(default_factory=list)


class VideoSourceProcessor(Protocol):
    async def prepare_first_pass_video_sources(self, *, videos, max_image_bytes: int, max_video_bytes: int): ...
