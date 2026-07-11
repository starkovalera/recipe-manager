import enum
from dataclasses import dataclass


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
            "url": self.url,
            "original_name": self.original_name,
            "error": self.error,
        }
