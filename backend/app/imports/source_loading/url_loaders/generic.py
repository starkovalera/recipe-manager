import re
from html import unescape
from urllib.parse import urljoin

from app.imports.source_loading.remote_fetch import FetchErrorCode, RemoteFetcher, RemoteFetchError, stable_fetch_error_code
from app.imports.source_loading.results import (
    SecondaryResourceKind,
    SecondaryResourceLoadResult,
    SecondaryResourceLoadStatus,
)
from app.imports.source_loading.url_loaders.media import html_response_is_supported, image_mime_type
from app.imports.source_loading.url_loaders.types import Fetch, FetchResponse, LoadedRemoteImage, LoadedUrlContent

_remote_fetcher = RemoteFetcher()


async def httpx_fetch(url: str, max_bytes: int) -> FetchResponse:
    response = await _remote_fetcher.fetch_bounded(url, max_bytes)
    return FetchResponse(content=response.content, headers=response.headers, final_url=response.final_url)


def _meta_content(html: str, key: str) -> str | None:
    pattern = rf'<meta\s+[^>]*(?:property|name)=["\']{re.escape(key)}["\'][^>]*content=["\']([^"\']+)["\'][^>]*>'
    match = re.search(pattern, html, flags=re.IGNORECASE)
    return unescape(match.group(1)).strip() if match else None


def _body_text(html: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", unescape(without_tags)).strip()


class GenericUrlContentLoader:
    def __init__(self, fetch: Fetch = httpx_fetch):
        self.fetch = fetch

    def supports(self, url: str) -> bool:
        return True

    async def load(self, url: str, max_images: int, max_image_bytes: int, max_videos: int = 0) -> LoadedUrlContent:
        page = await self.fetch(url, 256_000)
        if not html_response_is_supported(page):
            raise RemoteFetchError(FetchErrorCode.RESPONSE_TYPE_UNSUPPORTED)
        html = page.content.decode("utf-8", errors="replace")
        description = _meta_content(html, "og:description")
        text = description or _body_text(html)
        image_url = _meta_content(html, "og:image")
        images: list[LoadedRemoteImage] = []
        resource_results: list[SecondaryResourceLoadResult] = []
        if image_url and max_images > 0:
            effective_url = getattr(page, "final_url", "") or url
            resolved = urljoin(effective_url, image_url)
            try:
                image = await self.fetch(resolved, max_image_bytes)
                mime_type = image_mime_type(image)
                if mime_type is None:
                    raise RemoteFetchError(FetchErrorCode.RESPONSE_TYPE_UNSUPPORTED)
                images.append(
                    LoadedRemoteImage(
                        bytes=image.content,
                        mime_type=mime_type,
                        original_name="preview-image",
                        url=resolved,
                        position=0,
                    )
                )
            except Exception as error:
                resource_results.append(
                    SecondaryResourceLoadResult(
                        kind=SecondaryResourceKind.IMAGE,
                        status=SecondaryResourceLoadStatus.FAILED,
                        position=0,
                        url=resolved,
                        original_name="preview-image",
                        error=stable_fetch_error_code(error),
                    )
                )
        return LoadedUrlContent(url=url, text=text or None, images=images, resource_results=resource_results)
