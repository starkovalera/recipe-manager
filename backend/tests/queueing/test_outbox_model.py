from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import QueueOutboxMessage
from app.queueing.constants import QueueMessageType, QueueOutboxStatus


def test_outbox_message_defaults_to_pending():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        message = QueueOutboxMessage(
            message_type=QueueMessageType.IMPORT_JOB,
            entity_id="job-1",
        )
        session.add(message)
        session.commit()
        session.refresh(message)

        assert message.id
        assert message.message_type is QueueMessageType.IMPORT_JOB
        assert message.entity_id == "job-1"
        assert message.status is QueueOutboxStatus.PENDING
        assert message.attempt_count == 0
        assert message.last_attempt_at is None
        assert message.last_error_type is None
        assert message.published_at is None
        assert message.created_at is not None


def test_outbox_allows_multiple_messages_for_same_entity():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(
            [
                QueueOutboxMessage(
                    message_type=QueueMessageType.ACCOUNT_DELETION,
                    entity_id="user-1",
                ),
                QueueOutboxMessage(
                    message_type=QueueMessageType.ACCOUNT_DELETION,
                    entity_id="user-1",
                ),
            ]
        )
        session.commit()

        assert session.query(QueueOutboxMessage).count() == 2
