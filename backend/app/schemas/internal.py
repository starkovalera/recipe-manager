from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field, field_serializer

from app.models import (
    ImportEventType,
    ImportJobSource,
    JobEvent,
    Recipe,
    RecipeEmbeddingEvent,
    RecipeEmbeddingEventType,
    RecipeEmbeddingStatus,
)
from app.schemas.base import CamelModel

EVENT_STATUS_MAP = {
    ImportEventType.IMPORT_CREATED: "queued",
    ImportEventType.IMPORT_STARTED: "running",
    ImportEventType.RECIPE_CREATED: None,
    ImportEventType.IMPORT_FAILED: "failed",
}


class InternalImportJobSourceOut(CamelModel):
    id: str
    type: str
    status: str
    url: str | None = None
    original_name: str | None = None
    position: int
    error_code: str | None = None
    error_message: str | None = None


class InternalJobEventOut(CamelModel):
    id: str
    event_type: ImportEventType | str
    status_after: str | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime | None = None

    @field_serializer("event_type")
    def serialize_event_type(self, value: ImportEventType | str) -> str:
        return value.value if isinstance(value, ImportEventType) else value


class InternalStatusHistoryOut(CamelModel):
    status: str
    changed_at: datetime | None = None


def _status_history(job) -> list[InternalStatusHistoryOut]:
    history: list[InternalStatusHistoryOut] = []
    events = getattr(job, "event_items", getattr(job, "events", []))
    for event in sorted(events, key=lambda item: item.created_at):
        current_status = job.status.value if hasattr(job.status, "value") else job.status
        if event.event_type == ImportEventType.RECIPE_CREATED:
            status = (event.payload or {}).get("status") or current_status
        else:
            status = EVENT_STATUS_MAP.get(event.event_type)
        if status:
            history.append(InternalStatusHistoryOut(status=status, changed_at=event.created_at))
    if not history:
        status = job.status.value if hasattr(job.status, "value") else job.status
        history.append(InternalStatusHistoryOut(status=status, changed_at=job.updated_at))
    return history


class InternalImportJobOut(CamelModel):
    id: str
    owner_id: str
    client_id: str
    client_import_id: str | None = None
    dedupe_key: str | None = None
    status: str
    error_code: str | None = None
    error_message: str | None = None
    created_recipe_id: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime | None = Field(default=None, exclude=True)
    source_items: list[ImportJobSource] = Field(default_factory=list, validation_alias="sources", exclude=True)
    event_items: list[JobEvent] = Field(default_factory=list, validation_alias="events", exclude=True)

    @computed_field
    @property
    def status_history(self) -> list[InternalStatusHistoryOut]:
        return _status_history(self)

    @computed_field
    @property
    def sources(self) -> list[InternalImportJobSourceOut]:
        return [InternalImportJobSourceOut.model_validate(source) for source in sorted(self.source_items, key=lambda item: item.position)]

    @computed_field
    @property
    def events(self) -> list[InternalJobEventOut]:
        return [InternalJobEventOut.model_validate(event) for event in sorted(self.event_items, key=lambda item: item.created_at)]


class InternalImportJobListOut(BaseModel):
    items: list[InternalImportJobOut]


class InternalRecipeEmbeddingOut(CamelModel):
    recipe_id: str
    status: RecipeEmbeddingStatus
    model: str
    input_hash: str | None = None
    failed_attempts: int
    error_message: str | None = None
    last_attempt_at: datetime | None = None
    last_error_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    recipe_item: Recipe | None = Field(default=None, validation_alias="recipe", exclude=True)
    event_items: list[RecipeEmbeddingEvent] = Field(default_factory=list, validation_alias="events", exclude=True)

    @computed_field
    @property
    def owner_id(self) -> str | None:
        return self.recipe_item.owner_id if self.recipe_item is not None else None

    @computed_field
    @property
    def recipe_title(self) -> str | None:
        return self.recipe_item.title if self.recipe_item is not None else None

    @computed_field
    @property
    def events(self) -> list[InternalRecipeEmbeddingEventOut]:
        return [
            InternalRecipeEmbeddingEventOut.model_validate(event)
            for event in sorted(self.event_items, key=lambda item: item.created_at, reverse=True)
        ]


class InternalRecipeEmbeddingEventOut(CamelModel):
    id: str
    event_type: RecipeEmbeddingEventType
    status_after: RecipeEmbeddingStatus | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime | None = None


class InternalRecipeEmbeddingListOut(BaseModel):
    items: list[InternalRecipeEmbeddingOut]
