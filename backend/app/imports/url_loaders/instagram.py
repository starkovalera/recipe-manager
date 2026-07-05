import json
import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.core.logging import log_error, log_info
from app.imports.url_loaders.generic import GenericUrlContentLoader, httpx_fetch
from app.imports.url_loaders.types import Fetch, LoadedRemoteImage, LoadedRemoteVideo, LoadedUrlContent

logger = logging.getLogger("recipes.url.instagram")
SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_EMBED_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class ImageDescriptor:
    url: str
    position: int


@dataclass(frozen=True)
class VideoDescriptor:
    url: str
    poster_url: str | None
    position: int


def _instagram_post_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    match = re.match(r"^/(?:[^/]+/)?(?:p|reel)/([^/]+)", parsed.path)
    if not match:
        raise ValueError("Unsupported Instagram post URL.")
    kind = "reel" if "/reel/" in parsed.path else "p"
    return f"https://www.instagram.com/{kind}/{match.group(1)}/"


def _instagram_embed_url(raw_url: str) -> str:
    return f"{_instagram_post_url(raw_url)}embed/captioned/"


def _parse_context_json(html: str) -> dict:
    match = re.search(r'"contextJSON":"((?:\\.|[^"\\])*)"', html)
    if not match:
        raise ValueError("Instagram embed context was not found.")
    context_text = json.loads(f'"{match.group(1)}"')
    parsed = json.loads(context_text)
    return parsed if isinstance(parsed, dict) else {}


def _caption_text(media: dict) -> str:
    edges = media.get("edge_media_to_caption", {}).get("edges", [])
    if edges and isinstance(edges[0], dict):
        return str(edges[0].get("node", {}).get("text") or "")
    return ""


def _author_name(media: dict) -> str | None:
    username = media.get("owner", {}).get("username")
    return username.strip() if isinstance(username, str) and username.strip() else None


def _largest_resource(resources: list[dict] | None) -> dict | None:
    best: dict | None = None
    for resource in resources or []:
        if not resource.get("src"):
            continue
        if best is None:
            best = resource
            continue
        area = int(resource.get("config_width") or 0) * int(resource.get("config_height") or 0)
        best_area = int(best.get("config_width") or 0) * int(best.get("config_height") or 0)
        if area > best_area:
            best = resource
    return best


def _photo_nodes(media: dict) -> list[dict]:
    edges = media.get("edge_sidecar_to_children", {}).get("edges")
    if isinstance(edges, list) and edges:
        return [edge.get("node") for edge in edges if isinstance(edge, dict) and isinstance(edge.get("node"), dict)]
    return [media]


def _image_descriptors(media: dict, max_images: int) -> list[ImageDescriptor]:
    descriptors: list[ImageDescriptor] = []
    if max_images <= 0:
        return descriptors
    for node in _photo_nodes(media):
        if node.get("is_video"):
            continue
        resource = _largest_resource(node.get("display_resources"))
        if not resource:
            continue
        descriptors.append(ImageDescriptor(url=str(resource["src"]), position=len(descriptors)))
        if len(descriptors) >= max_images:
            break
    return descriptors


def _video_descriptors(media: dict, max_videos: int) -> list[VideoDescriptor]:
    descriptors: list[VideoDescriptor] = []
    if max_videos <= 0:
        return descriptors
    for node in _photo_nodes(media):
        video_url = node.get("video_url")
        if not node.get("is_video") or not video_url:
            continue
        poster = _largest_resource(node.get("display_resources"))
        descriptors.append(
            VideoDescriptor(
                url=str(video_url),
                poster_url=str(poster["src"]) if poster and poster.get("src") else None,
                position=len(descriptors),
            )
        )
        if len(descriptors) >= max_videos:
            break
    return descriptors


async def _fetch_instagram_embed(
    raw_url: str,
    fetch: Fetch,
    max_images: int,
    max_videos: int,
) -> tuple[str, str | None, str, list[ImageDescriptor], list[VideoDescriptor]]:
    normalized_url = _instagram_post_url(raw_url)
    response = await fetch(_instagram_embed_url(raw_url), MAX_EMBED_BYTES)
    html = response.content.decode("utf-8", errors="replace")
    context = _parse_context_json(html)
    media = context.get("gql_data", {}).get("shortcode_media")
    if not isinstance(media, dict):
        raise ValueError("Instagram embed media was not found.")
    descriptors = _image_descriptors(media, max_images)
    videos = _video_descriptors(media, max_videos)
    return normalized_url, _author_name(media), _caption_text(media), descriptors, videos


def _original_name_from_url(url: str) -> str:
    name = urlparse(url).path.split("/")[-1]
    return name if re.search(r"\.[a-z0-9]+$", name, re.IGNORECASE) else "url-slide-image"


def _original_video_name_from_url(url: str) -> str:
    name = urlparse(url).path.split("/")[-1]
    return name if re.search(r"\.[a-z0-9]+$", name, re.IGNORECASE) else "instagram-video.mp4"


async def _download_image(descriptor: ImageDescriptor, fetch: Fetch, max_image_bytes: int) -> LoadedRemoteImage | None:
    response = await fetch(descriptor.url, max_image_bytes)
    mime_type = response.headers.get("content-type", "").split(";")[0].lower()
    if mime_type not in SUPPORTED_IMAGE_TYPES:
        return None
    if not response.content:
        return None
    return LoadedRemoteImage(
        bytes=response.content,
        mime_type=mime_type,
        original_name=_original_name_from_url(descriptor.url),
        url=descriptor.url,
        position=descriptor.position,
    )


class InstagramUrlContentLoader:
    def __init__(self, fetch: Fetch = httpx_fetch):
        self.fetch = fetch
        self.fallback = GenericUrlContentLoader(fetch=fetch)

    def supports(self, url: str) -> bool:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        return bool(re.search(r"(^|\.)instagram\.com$", host) and re.search(r"/(?:[^/]+/)?(?:p|reel)/", parsed.path))

    async def load(self, url: str, max_images: int, max_image_bytes: int, max_videos: int = 1) -> LoadedUrlContent:
        try:
            normalized_url, author_name, text, descriptors, video_descriptors = await _fetch_instagram_embed(
                url, self.fetch, max_images, max_videos
            )
        except Exception as error:
            log_error(logger, "[recipes.url.instagram] Load fallback", error=repr(error), url=url)
            return await self.fallback.load(url, max_images=max_images, max_image_bytes=max_image_bytes)
        images: list[LoadedRemoteImage] = []
        for descriptor in descriptors:
            try:
                image = await _download_image(descriptor, self.fetch, max_image_bytes)
            except Exception as error:
                log_error(logger, "[recipes.url.instagram] Image download failed", error=repr(error), url=descriptor.url, position=descriptor.position)
                raise
            if image is None:
                raise ValueError(f"Instagram image could not be downloaded: {descriptor.url}")
            images.append(image)
        log_info(
            logger,
            "[recipes.url.instagram] Loaded Instagram content",
            url=normalized_url,
            detectedImageCount=len(descriptors),
            acceptedImageCount=len(images),
            detectedVideoCount=len(video_descriptors),
        )
        videos = [
            LoadedRemoteVideo(
                url=descriptor.url,
                poster_url=descriptor.poster_url,
                position=descriptor.position,
                original_name=_original_video_name_from_url(descriptor.url),
            )
            for descriptor in video_descriptors
        ]
        return LoadedUrlContent(
            url=normalized_url,
            author_name=author_name,
            text=text or f"URL: {normalized_url}",
            images=images,
            videos=videos,
        )
