from datetime import datetime

from pydantic import Field, computed_field

from app.core.config import get_settings
from app.models import ImportJobSource, SourceType
from app.schemas.base import CamelModel


class ImportJobSourceOut(CamelModel):
    type: SourceType
    url: str | None = None
    original_name: str | None = None
    text: str | None = None
    image_storage_key: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def media_url(self) -> str | None:
        return f"/media/{self.image_storage_key}" if self.image_storage_key else None


class ImportJobOut(CamelModel):
    job_id: str = Field(validation_alias="id")
    status: str
    created_recipe_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    attempt_count: int
    max_attempts: int = Field(default_factory=lambda: get_settings().max_import_attempts)
    source_items: list[ImportJobSource] = Field(default_factory=list, validation_alias="sources", exclude=True)

    @computed_field
    @property
    def sources(self) -> list[ImportJobSourceOut]:
        return [ImportJobSourceOut.model_validate(source) for source in sorted(self.source_items, key=lambda item: item.position)]
