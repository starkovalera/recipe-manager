from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models import QueueOutboxMessage
from app.queueing.constants import QueueMessageType, QueueOutboxStatus


def has_pending_outbox_message(
    session: Session,
    message_type: QueueMessageType,
    entity_id: str,
) -> bool:
    return bool(
        session.scalar(
            select(
                exists().where(
                    QueueOutboxMessage.status == QueueOutboxStatus.PENDING,
                    QueueOutboxMessage.message_type == message_type,
                    QueueOutboxMessage.entity_id == entity_id,
                )
            )
        )
    )


def get_outbox_message(
    session: Session,
    message_id: str,
    *,
    for_update: bool = False,
) -> QueueOutboxMessage | None:
    if for_update:
        statement = select(QueueOutboxMessage).where(QueueOutboxMessage.id == message_id).with_for_update()
        return session.scalar(statement)
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
