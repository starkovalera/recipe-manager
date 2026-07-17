from sqlalchemy.orm import Session

from app.models import QueueOutboxMessage
from app.queueing.constants import QueueMessageType


def schedule_outbox_message(
    session: Session,
    message_type: QueueMessageType,
    entity_id: str,
) -> QueueOutboxMessage:
    message = QueueOutboxMessage(
        message_type=message_type,
        entity_id=entity_id,
    )
    session.add(message)
    session.flush()
    return message
