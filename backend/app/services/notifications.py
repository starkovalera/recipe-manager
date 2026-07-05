from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotificationNotFoundError
from app.models import Notification
from app.notifications.queries import get_notification, mark_unread_notifications_read_through
from app.schemas.notifications import NotificationsMarkAllReadOut


def create_notification(
    session: Session,
    *,
    owner_id: str,
    type: str,
    title: str,
    message: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    data: dict[str, Any] | None = None,
) -> Notification:
    notification = Notification(
        owner_id=owner_id,
        type=type,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        data=data,
    )
    session.add(notification)
    return notification


def set_notification_status(session: Session, owner_id: str, notification_id: str, status: str) -> Notification:
    notification = get_notification(session, notification_id, owner_id)
    if notification is None:
        raise NotificationNotFoundError()
    notification.status = status
    notification.read_at = datetime.now(timezone.utc) if status == "read" else None
    session.commit()
    session.refresh(notification)
    return notification


def mark_notifications_read_through(
    session: Session,
    owner_id: str,
    last_notification_id: str,
) -> NotificationsMarkAllReadOut:
    target = get_notification(session, last_notification_id, owner_id)
    if target is None:
        raise NotificationNotFoundError()

    read_at = datetime.now(timezone.utc)
    updated_count = mark_unread_notifications_read_through(session, owner_id, target.created_at, read_at)
    session.commit()
    return NotificationsMarkAllReadOut(updated_count=updated_count)
