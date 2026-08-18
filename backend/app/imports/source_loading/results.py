import enum
import ipaddress
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.imports.source_loading.remote_fetch import FetchErrorCode

_SAFE_ERROR_CODES = frozenset(code.value for code in FetchErrorCode) | {"UNEXPECTED_ERROR"}
_REDACTED_URL = "<redacted-url>"


def _diagnostic_url(url: str | None) -> str | None:
    if url is None:
        return None
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        if parsed.scheme.lower() not in {"http", "https"} or not hostname or parsed.username or parsed.password:
            return _REDACTED_URL
        port = parsed.port
    except ValueError:
        return _REDACTED_URL

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        return _REDACTED_URL

    normalized_host = hostname.lower()
    if ":" in normalized_host:
        normalized_host = f"[{normalized_host}]"
    default_port = (parsed.scheme.lower() == "https" and port == 443) or (parsed.scheme.lower() == "http" and port == 80)
    port_suffix = f":{port}" if port is not None and not default_port else ""
    return f"{parsed.scheme.lower()}://{normalized_host}{port_suffix}"


def _diagnostic_error(error: str | None) -> str | None:
    if error is None or error in _SAFE_ERROR_CODES:
        return error
    return "UNEXPECTED_ERROR"


class SecondaryResourceLoadStatus(str, enum.Enum):
    LOADED = "LOADED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class SecondaryResourceKind(str, enum.Enum):
    URL_CONTENT = "URL_CONTENT"
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO_POSTER = "VIDEO_POSTER"
    VIDEO_TRANSCRIPT = "VIDEO_TRANSCRIPT"


@dataclass(frozen=True)
class SecondaryResourceLoadResult:
    kind: SecondaryResourceKind
    status: SecondaryResourceLoadStatus
    position: int | None = None
    url: str | None = None
    original_name: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "kind": self.kind.value,
            "status": self.status.value,
            "position": self.position,
            "url": _diagnostic_url(self.url),
            "original_name": self.original_name,
            "error": _diagnostic_error(self.error),
        }
