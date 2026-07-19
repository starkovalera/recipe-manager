from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as session_module
from app.db.base import Base
from app.models import QueueOutboxMessage
from app.queueing import outbox as outbox_module, reconcile_outbox as reconcile_module
from app.queueing.constants import QueueMessageType, QueueOutboxStatus
from app.queueing.outbox import reconcile_pending_outbox_messages


def create_session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


class SelectiveQueuePublisher:
    def __init__(self, failing_entity_id: str) -> None:
        self.failing_entity_id = failing_entity_id
        self.import_job_ids: list[str] = []

    def publish_import_job(self, import_job_id: str) -> None:
        self.import_job_ids.append(import_job_id)
        if import_job_id == self.failing_entity_id:
            raise RuntimeError("provider detail must not escape")

    def publish_recipe_embedding(self, recipe_id: str) -> None:
        raise AssertionError(f"Unexpected recipe embedding: {recipe_id}")

    def publish_account_deletion(self, user_id: str) -> None:
        raise AssertionError(f"Unexpected account deletion: {user_id}")


def test_reconcile_pending_outbox_messages_processes_one_oldest_bounded_batch(monkeypatch):
    session_factory = create_session_factory()
    publisher = SelectiveQueuePublisher("job-failed")
    created_at = datetime(2026, 7, 17, tzinfo=timezone.utc)

    monkeypatch.setattr(session_module, "SessionLocal", session_factory)
    monkeypatch.setattr(outbox_module, "get_queue_publisher", lambda: publisher)

    messages = [
        QueueOutboxMessage(
            id="published-message",
            message_type=QueueMessageType.IMPORT_JOB,
            entity_id="job-published",
            status=QueueOutboxStatus.PUBLISHED,
            created_at=created_at,
        ),
        QueueOutboxMessage(
            id="successful-message-1",
            message_type=QueueMessageType.IMPORT_JOB,
            entity_id="job-successful-1",
            created_at=created_at + timedelta(minutes=1),
        ),
        QueueOutboxMessage(
            id="failed-message",
            message_type=QueueMessageType.IMPORT_JOB,
            entity_id="job-failed",
            created_at=created_at + timedelta(minutes=2),
        ),
        QueueOutboxMessage(
            id="successful-message-2",
            message_type=QueueMessageType.IMPORT_JOB,
            entity_id="job-successful-2",
            created_at=created_at + timedelta(minutes=3),
        ),
        QueueOutboxMessage(
            id="beyond-limit-message",
            message_type=QueueMessageType.IMPORT_JOB,
            entity_id="job-beyond-limit",
            created_at=created_at + timedelta(minutes=4),
        ),
    ]
    with session_factory() as session:
        session.add_all(messages)
        session.commit()

    failed_ids = reconcile_pending_outbox_messages(batch_size=3)

    assert failed_ids == ["failed-message"]
    assert publisher.import_job_ids == [
        "job-successful-1",
        "job-failed",
        "job-successful-2",
    ]
    with session_factory() as session:
        assert session.get(QueueOutboxMessage, "successful-message-1").status is QueueOutboxStatus.PUBLISHED
        assert session.get(QueueOutboxMessage, "successful-message-2").status is QueueOutboxStatus.PUBLISHED
        assert session.get(QueueOutboxMessage, "failed-message").status is QueueOutboxStatus.PENDING
        assert session.get(QueueOutboxMessage, "published-message").attempt_count == 0
        assert session.get(QueueOutboxMessage, "beyond-limit-message").attempt_count == 0


def test_main_returns_zero_without_failures(monkeypatch):
    monkeypatch.setattr(
        reconcile_module,
        "get_settings",
        lambda: SimpleNamespace(outbox_reconcile_batch_size=25),
    )
    monkeypatch.setattr(
        reconcile_module,
        "reconcile_pending_outbox_messages",
        lambda **_kwargs: [],
    )

    assert reconcile_module.main() == 0


def test_main_returns_one_with_failures(monkeypatch):
    monkeypatch.setattr(
        reconcile_module,
        "get_settings",
        lambda: SimpleNamespace(outbox_reconcile_batch_size=25),
    )
    monkeypatch.setattr(
        reconcile_module,
        "reconcile_pending_outbox_messages",
        lambda **_kwargs: ["message-1"],
    )

    assert reconcile_module.main() == 1
