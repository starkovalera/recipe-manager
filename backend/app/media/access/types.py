from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from app.media.access.constants import DownloadAccessMode, MediaReferenceType
from app.storage.constants import StorageLocation


@dataclass(frozen=True)
class MediaReference:
    type: MediaReferenceType
    id: str


@dataclass(frozen=True)
class AuthorizedMedia:
    reference: MediaReference
    location: StorageLocation
    storage_key: str
    content_type: str


@dataclass(frozen=True)
class DownloadGrant:
    """A temporary retrieval grant whose access mode describes browser mechanics, not provider or visibility."""

    url: str
    expires_at: datetime | None
    content_type: str
    access_mode: DownloadAccessMode


class DownloadAccessProvider(Protocol):
    def create_grant(self, media: AuthorizedMedia) -> DownloadGrant: ...

    def get_local_path(self, media: AuthorizedMedia) -> Path: ...


class MediaReferenceUnavailableError(RuntimeError):
    """Authorized domain metadata cannot be used by the selected access provider."""
