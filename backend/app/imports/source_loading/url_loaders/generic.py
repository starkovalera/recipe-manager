import re
from html import unescape
from urllib.parse import urljoin

import httpx

from app.imports.source_loading.results import (
    SecondaryResourceKind,
    SecondaryResourceLoadResult,
    SecondaryResourceLoadStatus,
)
from app.imports.source_loading.url_loaders.types import Fetch, FetchResponse, LoadedRemoteImage, LoadedUrlContent

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def httpx_fetch(url: str, max_bytes: int) -> FetchResponse:
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
        response = await client.get(
            url,
            headers={
                "accept": "application/activity+json,application/json,text/html,*/*",
                "user-agent": "Mozilla/5.0 recipe-importer",
            },
        )
        response.raise_for_status()
        content = response.content[:max_bytes]
        return FetchResponse(content=content, headers={key.lower(): value for key, value in response.headers.items()})


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
        html = page.content.decode("utf-8", errors="replace")
        description = _meta_content(html, "og:description")
        text = description or _body_text(html)
        image_url = _meta_content(html, "og:image")
        images: list[LoadedRemoteImage] = []
        resource_results: list[SecondaryResourceLoadResult] = []
        if image_url and max_images > 0:
            resolved = urljoin(url, image_url)
            try:
                image = await self.fetch(resolved, max_image_bytes)
                mime_type = image.headers.get("content-type", "application/octet-stream").split(";")[0]
                if not image.content or mime_type not in SUPPORTED_IMAGE_TYPES:
                    raise ValueError("Generic preview image is empty or has an unsupported content type.")
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
                        error=repr(error),
                    )
                )
        return LoadedUrlContent(url=url, text=text or None, images=images, resource_results=resource_results)
