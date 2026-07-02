from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Notification


def get_notification(session: Session, notification_id: str, owner_id: str) -> Notification | None:
    return session.scalar(select(Notification).where(Notification.id == notification_id, Notification.owner_id == owner_id))


def list_notifications(session: Session, owner_id: str) -> list[Notification]:
    return session.scalars(
        select(Notification)
        .where(Notification.owner_id == owner_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
    ).all()


def mark_unread_notifications_read_through(
    session: Session,
    owner_id: str,
    target_created_at: datetime,
    read_at: datetime,
) -> int:
    result = session.execute(
        update(Notification)
        .where(
            Notification.owner_id == owner_id,
            Notification.status == "unread",
            Notification.created_at <= target_created_at,
        )
        .values(status="read", read_at=read_at)
    )
    return result.rowcount or 0
