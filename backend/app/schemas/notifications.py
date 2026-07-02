from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.schemas.base import CamelModel


class NotificationOut(CamelModel):
    id: str
    type: str
    status: str
    title: str
    message: str
    entity_type: str | None = None
    entity_id: str | None = None
    data: dict[str, Any] | None = None
    read_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class NotificationListOut(BaseModel):
    items: list[NotificationOut]


class NotificationPatchIn(BaseModel):
    status: Literal["read", "unread"]


class NotificationsMarkAllReadIn(CamelModel):
    last_notification_id: str


class NotificationsMarkAllReadOut(CamelModel):
    updated_count: int
