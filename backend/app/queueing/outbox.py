import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import bind_logger
from app.db.session import db_session
from app.models import QueueOutboxMessage
from app.queueing.constants import QueueMessageType, QueueOutboxStatus
from app.queueing.provider import get_queue_publisher
from app.queueing.queries import get_outbox_message, list_pending_outbox_message_ids

OUTBOX_LOG_COMPONENT = "recipes.queueing.outbox"
logger = bind_logger(
    logging.getLogger(__name__),
    component=OUTBOX_LOG_COMPONENT,
)


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


def _publish_message(
    message_type: QueueMessageType,
    entity_id: str,
) -> None:
    publisher = get_queue_publisher()

    if message_type is QueueMessageType.IMPORT_JOB:
        publisher.publish_import_job(entity_id)
        return
    if message_type is QueueMessageType.RECIPE_EMBEDDING:
        publisher.publish_recipe_embedding(entity_id)
        return
    if message_type is QueueMessageType.ACCOUNT_DELETION:
        publisher.publish_account_deletion(entity_id)
        return

    raise RuntimeError(f"Unsupported queue message type: {message_type.value}")


def _record_publish_failure(
    message_id: str,
    *,
    attempted_at: datetime,
    error_type: str,
) -> None:
    with db_session() as session:
        message = get_outbox_message(
            session,
            message_id,
            for_update=True,
        )
        if message is None or message.status is QueueOutboxStatus.PUBLISHED:
            return
        message.attempt_count += 1
        message.last_attempt_at = attempted_at
        message.last_error_type = error_type


def _record_publish_success(
    message_id: str,
    *,
    attempted_at: datetime,
) -> bool:
    with db_session() as session:
        message = get_outbox_message(
            session,
            message_id,
            for_update=True,
        )
        if message is None:
            return False
        if message.status is QueueOutboxStatus.PUBLISHED:
            return True

        if message.message_type is QueueMessageType.RECIPE_EMBEDDING:
            from app.embeddings.outbox import record_embedding_enqueued

            record_embedding_enqueued(session, message.entity_id)

        message.attempt_count += 1
        message.last_attempt_at = attempted_at
        message.last_error_type = None
        message.status = QueueOutboxStatus.PUBLISHED
        message.published_at = attempted_at
    return True


def dispatch_outbox_message(message_id: str) -> bool:
    with db_session() as session:
        message = get_outbox_message(session, message_id)
        if message is None:
            logger.error(
                "Queue outbox message not found.",
                outbox_message_id=message_id,
            )
            return False
        if message.status is QueueOutboxStatus.PUBLISHED:
            return True
        message_type = message.message_type
        entity_id = message.entity_id

    attempted_at = datetime.now(timezone.utc)

    try:
        _publish_message(message_type, entity_id)
    except Exception as error:
        error_type = type(error).__name__
        try:
            _record_publish_failure(
                message_id,
                attempted_at=attempted_at,
                error_type=error_type,
            )
        except Exception as persistence_error:
            logger.error(
                "Queue outbox failure metadata persistence failed.",
                outbox_message_id=message_id,
                message_type=message_type.value,
                entity_id=entity_id,
                error_type=type(persistence_error).__name__,
            )
        logger.error(
            "Queue outbox publication failed.",
            outbox_message_id=message_id,
            message_type=message_type.value,
            entity_id=entity_id,
            error_type=error_type,
        )
        return False
    try:
        return _record_publish_success(
            message_id,
            attempted_at=attempted_at,
        )
    except Exception as error:
        logger.error(
            "Queue outbox success persistence failed.",
            outbox_message_id=message_id,
            message_type=message_type.value,
            entity_id=entity_id,
            error_type=type(error).__name__,
        )
        return False


def reconcile_pending_outbox_messages(
    *,
    batch_size: int,
) -> list[str]:
    with db_session() as session:
        message_ids = list_pending_outbox_message_ids(
            session,
            limit=batch_size,
        )

    return [message_id for message_id in message_ids if not dispatch_outbox_message(message_id)]
