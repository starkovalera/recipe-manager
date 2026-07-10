from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.config import get_settings
from app.models import ImportJob, ImportJobErrorCode, ImportJobSource, ImportJobStatus, ImportSourceStatus, SourceType


def _datetime_to_str(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@dataclass(frozen=True)
class ImportJobSourceContext:
    id: str | None
    type: SourceType
    position: int
    status: ImportSourceStatus
    url: str | None = None
    text: str | None = None
    image_storage_key: str | None = None
    original_name: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None

    @classmethod
    def from_source(cls, source: ImportJobSource) -> ImportJobSourceContext:
        return cls(
            id=source.id,
            type=source.type,
            position=source.position,
            status=source.status,
            url=source.url,
            text=source.text,
            image_storage_key=source.image_storage_key,
            original_name=source.original_name,
            mime_type=source.mime_type,
            size_bytes=source.size_bytes,
        )


@dataclass(frozen=True)
class ImportJobContext:
    id: str | None
    owner_id: str
    client_id: str
    client_import_id: str | None
    dedupe_key: str | None
    status: ImportJobStatus
    error_code: ImportJobErrorCode | None
    error_message: str | None
    created_recipe_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    recipe_language: str
    sources: tuple[ImportJobSourceContext, ...]

    @classmethod
    def from_job(cls, job: ImportJob) -> ImportJobContext:
        language = get_settings().recipe_language
        if job.owner and job.owner.settings:
            language = job.owner.settings.recipe_language
        return cls(
            id=job.id,
            owner_id=job.owner_id,
            client_id=job.client_id,
            client_import_id=job.client_import_id,
            dedupe_key=job.dedupe_key,
            status=job.status,
            error_code=job.error_code,
            error_message=job.error_message,
            created_recipe_id=job.created_recipe_id,
            started_at=job.started_at,
            finished_at=job.finished_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
            recipe_language=language,
            sources=tuple(ImportJobSourceContext.from_source(source) for source in job.sources),
        )

    @property
    def image_storage_keys(self) -> list[str]:
        return [source.image_storage_key for source in self.sources if source.image_storage_key]

    @property
    def is_single_url_import(self) -> bool:
        return len(self.sources) == 1 and self.sources[0].type == SourceType.URL

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "client_id": self.client_id,
            "client_import_id": self.client_import_id,
            "dedupe_key": self.dedupe_key,
            "status": self.status.value,
            "error_code": self.error_code.value if self.error_code else None,
            "error_message": self.error_message,
            "created_recipe_id": self.created_recipe_id,
            "started_at": _datetime_to_str(self.started_at),
            "finished_at": _datetime_to_str(self.finished_at),
            "created_at": _datetime_to_str(self.created_at),
            "updated_at": _datetime_to_str(self.updated_at),
        }

