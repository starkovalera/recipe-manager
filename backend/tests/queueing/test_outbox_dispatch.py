from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import QueueOutboxMessage
from app.queueing.constants import QueueMessageType, QueueOutboxStatus
from app.queueing.outbox import schedule_outbox_message
from app.queueing.queries import (
    get_outbox_message,
    list_pending_outbox_message_ids,
)


def create_session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_schedule_outbox_message_uses_supplied_transaction():
    session_factory = create_session_factory()

    with session_factory() as session:
        with session.begin():
            message = schedule_outbox_message(
                session,
                QueueMessageType.IMPORT_JOB,
                "job-1",
            )
            message_id = message.id

    with session_factory() as session:
        persisted = session.get(QueueOutboxMessage, message_id)
        assert persisted is not None
        assert persisted.entity_id == "job-1"
        assert persisted.status is QueueOutboxStatus.PENDING


def test_schedule_outbox_message_rolls_back_with_caller_transaction():
    session_factory = create_session_factory()

    with pytest.raises(RuntimeError, match="rollback"):
        with session_factory() as session:
            with session.begin():
                schedule_outbox_message(
                    session,
                    QueueMessageType.IMPORT_JOB,
                    "job-1",
                )
                raise RuntimeError("rollback")

    with session_factory() as session:
        assert session.query(QueueOutboxMessage).count() == 0


def test_get_outbox_message_returns_message_or_none():
    session_factory = create_session_factory()

    with session_factory() as session:
        message = QueueOutboxMessage(
            message_type=QueueMessageType.IMPORT_JOB,
            entity_id="job-1",
        )
        session.add(message)
        session.commit()

        assert get_outbox_message(session, message.id) is message
        assert get_outbox_message(session, "missing-message") is None


def test_list_pending_outbox_message_ids_returns_oldest_limited_batch():
    session_factory = create_session_factory()
    created_at = datetime(2026, 7, 17, tzinfo=timezone.utc)

    with session_factory() as session:
        session.add_all(
            [
                QueueOutboxMessage(
                    id="pending-2",
                    message_type=QueueMessageType.IMPORT_JOB,
                    entity_id="job-2",
                    created_at=created_at + timedelta(minutes=2),
                ),
                QueueOutboxMessage(
                    id="published-1",
                    message_type=QueueMessageType.IMPORT_JOB,
                    entity_id="job-published",
                    status=QueueOutboxStatus.PUBLISHED,
                    created_at=created_at,
                ),
                QueueOutboxMessage(
                    id="pending-1",
                    message_type=QueueMessageType.IMPORT_JOB,
                    entity_id="job-1",
                    created_at=created_at + timedelta(minutes=1),
                ),
                QueueOutboxMessage(
                    id="pending-3",
                    message_type=QueueMessageType.IMPORT_JOB,
                    entity_id="job-3",
                    created_at=created_at + timedelta(minutes=3),
                ),
            ]
        )
        session.commit()

        assert list_pending_outbox_message_ids(session, limit=2) == [
            "pending-1",
            "pending-2",
        ]
