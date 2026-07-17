from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import QueueOutboxMessage
from app.queueing.constants import QueueOutboxStatus


def get_outbox_message(
    session: Session,
    message_id: str,
) -> QueueOutboxMessage | None:
    return session.get(QueueOutboxMessage, message_id)


def list_pending_outbox_message_ids(
    session: Session,
    *,
    limit: int,
) -> list[str]:
    statement = (
        select(QueueOutboxMessage.id)
        .where(QueueOutboxMessage.status == QueueOutboxStatus.PENDING)
        .order_by(
            QueueOutboxMessage.created_at,
            QueueOutboxMessage.id,
        )
        .limit(limit)
    )
    return list(session.scalars(statement))
