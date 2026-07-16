import json
import re
from html import unescape
from urllib.parse import urlparse

from app.imports.source_loading.url_loaders.generic import httpx_fetch
from app.imports.source_loading.url_loaders.types import Fetch, LoadedRemoteImage, LoadedUrlContent

FIXTURE_SCRIPT_ID = "recipe-manager-fixture"


def host_matches(url: str, allowed_hosts: set[str]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in allowed_hosts


def fixture_payload(html: str) -> dict:
    pattern = (
        rf'<script\s+[^>]*id=["\']{FIXTURE_SCRIPT_ID}["\'][^>]*>'
        r"(.*?)"
        r"</script>"
    )
    match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return {}
    content = unescape(match.group(1)).strip()
    return json.loads(content) if content else {}


async def load_platform_fixture(
    url: str,
    fetch: Fetch,
    max_images: int,
    max_image_bytes: int,
) -> LoadedUrlContent:
    page = await fetch(url, 512_000)
    html = page.content.decode("utf-8", errors="replace")
    payload = fixture_payload(html)
    images: list[LoadedRemoteImage] = []
    for position, media in enumerate(payload.get("media", [])):
        if len(images) >= max_images:
            break
        if media.get("type") != "image" or not media.get("url"):
            continue
        image_url = str(media["url"])
        image = await fetch(image_url, max_image_bytes)
        mime_type = image.headers.get("content-type", "application/octet-stream").split(";")[0]
        images.append(
            LoadedRemoteImage(
                bytes=image.content,
                mime_type=mime_type,
                original_name=f"platform-image-{position}",
                url=image_url,
                position=position,
            )
        )
    return LoadedUrlContent(
        url=url,
        text=str(payload.get("caption") or ""),
        author_name=payload.get("authorName"),
        images=images,
    )


# Not wired into the production URL loader registry. This is a reusable base
# for fixture-style platform loaders if we reintroduce local HTML fixtures for
# social-platform parser tests.
class FixturePlatformLoader:
    allowed_hosts: set[str] = set()

    def __init__(self, fetch: Fetch = httpx_fetch):
        self.fetch = fetch

    def supports(self, url: str) -> bool:
        return host_matches(url, self.allowed_hosts)

    async def load(self, url: str, max_images: int, max_image_bytes: int) -> LoadedUrlContent:
        return await load_platform_fixture(url, self.fetch, max_images, max_image_bytes)
