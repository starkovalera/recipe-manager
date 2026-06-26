from dataclasses import dataclass
from urllib.parse import urlparse

from app.models import SourceName


def detect_source_name_from_url(raw_url: str) -> SourceName:
    try:
        hostname = (urlparse(raw_url).hostname or "").lower()
    except ValueError:
        return SourceName.OTHER

    if hostname == "instagram.com" or hostname.endswith(".instagram.com"):
        return SourceName.INSTAGRAM
    if hostname in {"threads.net", "threads.com"} or hostname.endswith(".threads.net") or hostname.endswith(".threads.com"):
        return SourceName.THREADS
    if hostname == "tiktok.com" or hostname.endswith(".tiktok.com") or hostname == "vm.tiktok.com":
        return SourceName.TT
    return SourceName.OTHER


@dataclass(frozen=True)
class SourceNameResult:
    ok: bool
    source_name: SourceName | None = None
    error_code: str | None = None


def derive_source_name(urls: list[str]) -> SourceNameResult:
    if not urls:
        return SourceNameResult(ok=True, source_name=SourceName.MANUAL)

    known_platforms = {detect_source_name_from_url(url) for url in urls}
    known_platforms.discard(SourceName.OTHER)

    if len(known_platforms) > 1:
        return SourceNameResult(ok=False, error_code="MIXED_SOURCE_PLATFORMS")
    if len(known_platforms) == 1:
        return SourceNameResult(ok=True, source_name=next(iter(known_platforms)))
    return SourceNameResult(ok=True, source_name=SourceName.OTHER)
