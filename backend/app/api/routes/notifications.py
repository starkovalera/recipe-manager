from fastapi import APIRouter

from app.api.deps import CurrentUserDep, SessionDep
from app.models import Notification
from app.notifications.queries import list_notifications
from app.schemas.notifications import (
    NotificationListOut,
    NotificationOut,
    NotificationPatchIn,
    NotificationsMarkAllReadIn,
    NotificationsMarkAllReadOut,
)
from app.services.notifications import mark_notifications_read_through, set_notification_status

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListOut)
def get_notifications(session: SessionDep, current_user: CurrentUserDep) -> dict[str, list[Notification]]:
    return {"items": list_notifications(session, current_user.id)}


@router.patch("/read-all", response_model=NotificationsMarkAllReadOut)
def mark_all_notifications_read(
    patch: NotificationsMarkAllReadIn,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> NotificationsMarkAllReadOut:
    return mark_notifications_read_through(session, current_user.id, patch.last_notification_id)


@router.patch("/{notification_id}", response_model=NotificationOut)
def patch_notification(
    notification_id: str,
    patch: NotificationPatchIn,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Notification:
    return set_notification_status(session, current_user.id, notification_id, patch.status)
