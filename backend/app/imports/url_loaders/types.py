from dataclasses import dataclass, field
from typing import Awaitable, Callable, Protocol


@dataclass(frozen=True)
class LoadedRemoteImage:
    bytes: bytes
    mime_type: str
    original_name: str
    url: str
    position: int


@dataclass(frozen=True)
class LoadedUrlContent:
    url: str
    text: str
    author_name: str | None = None
    images: list[LoadedRemoteImage] = field(default_factory=list)


@dataclass(frozen=True)
class FetchResponse:
    content: bytes
    headers: dict[str, str]


Fetch = Callable[[str, int], Awaitable[FetchResponse]]


class UrlContentLoader(Protocol):
    def supports(self, url: str) -> bool:
        raise NotImplementedError

    async def load(self, url: str, max_images: int, max_image_bytes: int) -> LoadedUrlContent:
        raise NotImplementedError
