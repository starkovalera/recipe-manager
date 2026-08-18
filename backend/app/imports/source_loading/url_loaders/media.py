from collections.abc import Mapping

from app.imports.source_loading.url_loaders.types import FetchResponse

SUPPORTED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
SUPPORTED_HTML_TYPES = frozenset({
    "application/json",
    "application/xhtml+xml",
    "text/html",
    "text/plain",
})


def normalized_content_type(headers: Mapping[str, str]) -> str | None:
    for name, value in headers.items():
        if name.lower() == "content-type":
            content_type = str(value).split(";", 1)[0].strip().lower()
            return content_type or None
    return None


def image_mime_type(response: FetchResponse) -> str | None:
    mime_type = normalized_content_type(response.headers)
    if response.content and mime_type in SUPPORTED_IMAGE_TYPES:
        return mime_type
    return None


def html_response_is_supported(response: FetchResponse) -> bool:
    content_type = normalized_content_type(response.headers)
    return content_type is None or content_type in SUPPORTED_HTML_TYPES


def video_response_is_supported(response: FetchResponse) -> bool:
    content_type = normalized_content_type(response.headers)
    return content_type is None or content_type == "application/octet-stream" or content_type.startswith("video/")
