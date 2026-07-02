import json
import logging
import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse

from app.core.logging import log_error, log_info
from app.imports.url_loaders.generic import httpx_fetch
from app.imports.url_loaders.types import Fetch, LoadedRemoteImage, LoadedRemoteVideo, LoadedUrlContent

logger = logging.getLogger("recipes.url.threads")
SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_HTML_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class ImageDescriptor:
    url: str
    position: int


@dataclass(frozen=True)
class VideoDescriptor:
    url: str
    poster_url: str | None
    position: int


def _decode_html(value: str) -> str:
    decoded = value
    for _ in range(3):
        next_value = unescape(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    return decoded


def _attr_value(tag: str, attr_name: str) -> str | None:
    match = re.search(rf"""\s{attr_name}\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""", tag, re.IGNORECASE)
    value = match.group(1) or match.group(2) or match.group(3) if match else None
    return _decode_html(value) if value is not None else None


def _meta_content(html: str, names: list[str]) -> str | None:
    for tag in re.findall(r"<meta\b[^>]*>", html, flags=re.IGNORECASE):
        name = (_attr_value(tag, "property") or _attr_value(tag, "name") or "").lower()
        if name in names:
            content = _attr_value(tag, "content")
            if content:
                return content
    return None


def _threads_post_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    match = re.match(r"^/(?:@[^/]+/post|t)/([^/]+)", parsed.path)
    if not match:
        raise ValueError("Unsupported Threads post URL.")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def _extract_script_json(html: str) -> list[object]:
    payloads: list[object] = []
    for match in re.finditer(r"<script\b[^>]*type=[\"']application/json[\"'][^>]*>([\s\S]*?)</script>", html, re.IGNORECASE):
        body = (match.group(1) or "").strip()
        if not body:
            continue
        try:
            payloads.append(json.loads(body))
        except json.JSONDecodeError:
            continue
    return payloads


def _visit(value: object, callback) -> None:
    if isinstance(value, list):
        for item in value:
            _visit(item, callback)
        return
    if not isinstance(value, dict):
        return
    callback(value)
    for child in value.values():
        _visit(child, callback)


def _extract_post_id(payloads: list[object]) -> str | None:
    post_id: str | None = None
    for payload in payloads:
        def capture(node: dict) -> None:
            nonlocal post_id
            if post_id is None and isinstance(node.get("postID"), str):
                post_id = node["postID"]

        _visit(payload, capture)
        if post_id:
            return post_id
    return None


def _is_threads_post(node: dict) -> bool:
    return isinstance(node.get("pk"), str) and (
        isinstance(node.get("carousel_media"), list)
        or isinstance(node.get("image_versions2"), dict)
        or isinstance(node.get("caption"), dict)
    )


def _is_thread_edge(value: object) -> bool:
    return isinstance(value, dict) and isinstance(value.get("node"), dict) and isinstance(value["node"].get("thread_items"), list)


def _collect_thread_edge_groups(payloads: list[object]) -> list[list[dict]]:
    groups: list[list[dict]] = []
    for payload in payloads:
        def capture(node: dict) -> None:
            for child in node.values():
                if not isinstance(child, list) or not child:
                    continue
                if all(_is_thread_edge(item) for item in child):
                    groups.append(child)

        _visit(payload, capture)
    return groups


def _posts_from_edge(edge: dict) -> list[dict]:
    items = edge.get("node", {}).get("thread_items", [])
    return [item["post"] for item in items if isinstance(item, dict) and isinstance(item.get("post"), dict) and item["post"].get("pk")]


def _matches_post(post: dict, post_id: str | None, shortcode: str) -> bool:
    return bool((post_id and post.get("pk") == post_id) or (shortcode and post.get("code") == shortcode))


def _same_author(post: dict, root: dict) -> bool:
    post_user = post.get("user") if isinstance(post.get("user"), dict) else {}
    root_user = root.get("user") if isinstance(root.get("user"), dict) else {}
    post_id = post_user.get("id")
    root_id = root_user.get("id")
    if post_id and root_id:
        return post_id == root_id
    username = str(post_user.get("username") or "").lower()
    root_username = str(root_user.get("username") or "").lower()
    if username and root_username:
        return username == root_username
    return post.get("pk") == root.get("pk")


def _dedupe_posts(posts: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for post in posts:
        key = post.get("pk") or post.get("code")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(post)
    return result


def _find_post(payloads: list[object], shortcode: str) -> dict | None:
    post_id = _extract_post_id(payloads)
    fallback: dict | None = None

    for payload in payloads:
        def capture(node: dict) -> None:
            nonlocal fallback
            if not _is_threads_post(node):
                return
            if post_id and node.get("pk") == post_id:
                fallback = node
                return
            if fallback is None and node.get("code") == shortcode:
                fallback = node

        _visit(payload, capture)
    return fallback


def _find_primary_thread_posts(payloads: list[object], shortcode: str) -> list[dict]:
    post_id = _extract_post_id(payloads)
    for edges in _collect_thread_edge_groups(payloads):
        root_index = next(
            (index for index, edge in enumerate(edges) if any(_matches_post(post, post_id, shortcode) for post in _posts_from_edge(edge))),
            -1,
        )
        if root_index < 0:
            continue
        root_post = next((post for post in _posts_from_edge(edges[root_index]) if _matches_post(post, post_id, shortcode)), None)
        if not root_post:
            continue
        posts: list[dict] = []
        for index in range(root_index, len(edges)):
            edge_posts = _posts_from_edge(edges[index])
            first_post = edge_posts[0] if edge_posts else None
            if not first_post:
                break
            if index != root_index and not _same_author(first_post, root_post):
                break
            posts.extend([post for post in edge_posts if _same_author(post, root_post)])
        deduped = _dedupe_posts(posts)
        if deduped:
            return deduped
    fallback = _find_post(payloads, shortcode)
    return [fallback] if fallback else []


def _largest_candidate(candidates: list[dict] | None) -> dict | None:
    best: dict | None = None
    for candidate in candidates or []:
        if not candidate.get("url"):
            continue
        if best is None:
            best = candidate
            continue
        area = int(candidate.get("width") or 0) * int(candidate.get("height") or 0)
        best_area = int(best.get("width") or 0) * int(best.get("height") or 0)
        if area > best_area:
            best = candidate
    return best


def _media_nodes(post: dict) -> list[dict]:
    carousel = post.get("carousel_media")
    return carousel if isinstance(carousel, list) and carousel else [post]


def _image_descriptors(posts: list[dict], max_images: int) -> list[ImageDescriptor]:
    descriptors: list[ImageDescriptor] = []
    if max_images <= 0:
        return descriptors
    for post in posts:
        for media in _media_nodes(post):
            if isinstance(media.get("video_versions"), list) and media["video_versions"]:
                continue
            candidate = _largest_candidate(media.get("image_versions2", {}).get("candidates") if isinstance(media.get("image_versions2"), dict) else None)
            if not candidate:
                continue
            descriptors.append(ImageDescriptor(url=str(candidate["url"]), position=len(descriptors)))
            if len(descriptors) >= max_images:
                return descriptors
    return descriptors


def _first_video_url(media: dict) -> str | None:
    versions = media.get("video_versions")
    if not isinstance(versions, list):
        return None
    for version in versions:
        if isinstance(version, dict) and isinstance(version.get("url"), str) and version["url"]:
            return version["url"]
    return None


def _video_descriptors(posts: list[dict], max_videos: int) -> list[VideoDescriptor]:
    descriptors: list[VideoDescriptor] = []
    if max_videos <= 0:
        return descriptors
    for post in posts:
        for media in _media_nodes(post):
            video_url = _first_video_url(media)
            if not video_url:
                continue
            poster = _largest_candidate(media.get("image_versions2", {}).get("candidates") if isinstance(media.get("image_versions2"), dict) else None)
            descriptors.append(
                VideoDescriptor(
                    url=video_url,
                    poster_url=str(poster["url"]) if poster and poster.get("url") else None,
                    position=len(descriptors),
                )
            )
            if len(descriptors) >= max_videos:
                return descriptors
    return descriptors


def _author_name(posts: list[dict]) -> str | None:
    for post in posts:
        user = post.get("user") if isinstance(post.get("user"), dict) else {}
        username = user.get("username")
        if isinstance(username, str) and username.strip():
            return username.strip()
    return None


def _original_name_from_url(url: str) -> str:
    name = urlparse(url).path.split("/")[-1]
    return name if re.search(r"\.[a-z0-9]+$", name, re.IGNORECASE) else "threads-image"


def _original_video_name_from_url(url: str) -> str:
    name = urlparse(url).path.split("/")[-1]
    return name if re.search(r"\.[a-z0-9]+$", name, re.IGNORECASE) else "threads-video.mp4"


async def _download_image(descriptor: ImageDescriptor, fetch: Fetch, max_image_bytes: int) -> LoadedRemoteImage | None:
    response = await fetch(descriptor.url, max_image_bytes)
    mime_type = response.headers.get("content-type", "").split(";")[0].lower()
    if mime_type not in SUPPORTED_IMAGE_TYPES or not response.content:
        return None
    return LoadedRemoteImage(
        bytes=response.content,
        mime_type=mime_type,
        original_name=_original_name_from_url(descriptor.url),
        url=descriptor.url,
        position=descriptor.position,
    )


class ThreadsUrlContentLoader:
    def __init__(self, fetch: Fetch = httpx_fetch):
        self.fetch = fetch

    def supports(self, url: str) -> bool:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        return bool(re.search(r"(^|\.)threads\.(?:com|net)$", host) and re.match(r"^/(?:@[^/]+/post|t)/", parsed.path))

    async def load(self, url: str, max_images: int, max_image_bytes: int, max_videos: int = 1) -> LoadedUrlContent:
        normalized_url = _threads_post_url(url)
        response = await self.fetch(normalized_url, MAX_HTML_BYTES)
        html = response.content.decode("utf-8", errors="replace")
        payloads = _extract_script_json(html)
        shortcode = normalized_url.rstrip("/").split("/")[-1]
        posts = _find_primary_thread_posts(payloads, shortcode)
        captions = [
            post.get("caption", {}).get("text", "").strip()
            for post in posts
            if isinstance(post.get("caption"), dict) and post.get("caption", {}).get("text", "").strip()
        ]
        descriptors = _image_descriptors(posts, max_images)
        video_descriptors = _video_descriptors(posts, max_videos)
        images: list[LoadedRemoteImage] = []
        for descriptor in descriptors:
            try:
                image = await _download_image(descriptor, self.fetch, max_image_bytes)
            except Exception as error:
                log_error(logger, "[recipes.url.threads] Image download failed", error=repr(error), url=descriptor.url, position=descriptor.position)
                image = None
            if image:
                images.append(image)
        text = "\n\n".join(captions) or _meta_content(html, ["og:description", "twitter:description", "description"]) or ""
        log_info(
            logger,
            "[recipes.url.threads] Loaded Threads content",
            url=normalized_url,
            detectedImageCount=len(descriptors),
            acceptedImageCount=len(images),
            detectedVideoCount=len(video_descriptors),
            postCount=len(posts),
        )
        return LoadedUrlContent(
            url=normalized_url,
            author_name=_author_name(posts),
            text=text or f"URL: {normalized_url}",
            images=images,
            videos=[
                LoadedRemoteVideo(
                    url=descriptor.url,
                    poster_url=descriptor.poster_url,
                    position=descriptor.position,
                    original_name=_original_video_name_from_url(descriptor.url),
                )
                for descriptor in video_descriptors
            ],
        )
