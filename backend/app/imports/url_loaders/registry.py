from dataclasses import dataclass
from urllib.parse import urlparse

from app.imports.url_loaders.types import UrlContentLoader


@dataclass(frozen=True)
class UrlNormalizeResult:
    value: str | None = None
    error_code: str | None = None
    error_message: str | None = None


def normalize_import_url(raw_url: str) -> UrlNormalizeResult:
    value = raw_url.strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return UrlNormalizeResult(error_code="INVALID_URL", error_message="Use an HTTP or HTTPS URL.")
    return UrlNormalizeResult(value=value)


class UrlContentLoaderRegistry:
    def __init__(self, loaders: list[UrlContentLoader]):
        self.loaders = loaders

    def loader_for(self, url: str) -> UrlContentLoader:
        for loader in self.loaders:
            if loader.supports(url):
                return loader
        raise ValueError(f"No URL loader for {url}")
