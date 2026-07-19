from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as session_module
from app.db.base import Base
from app.models import (
    QueueOutboxMessage,
    Recipe,
    RecipeEmbedding,
    RecipeEmbeddingEvent,
    RecipeEmbeddingEventType,
    RecipeEmbeddingStatus,
    User,
)
from app.queueing import outbox as outbox_module
from app.queueing.constants import QueueMessageType, QueueOutboxStatus
from app.queueing.outbox import dispatch_outbox_message, schedule_outbox_message
from app.queueing.queries import (
    get_outbox_message,
    list_pending_outbox_message_ids,
)
from app.queueing.sqs import SqsQueuePublisher

IMPORTS_QUEUE_URL = "https://sqs.example.test/000/imports"
EMBEDDINGS_QUEUE_URL = "https://sqs.example.test/000/embeddings"
ACCOUNT_DELETION_QUEUE_URL = "https://sqs.example.test/000/account-deletion"


def create_session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


class StubQueuePublisher:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.import_job_ids: list[str] = []
        self.recipe_ids: list[str] = []
        self.user_ids: list[str] = []

    def _raise_if_configured(self) -> None:
        if self.error is not None:
            raise self.error

    def publish_import_job(self, import_job_id: str) -> None:
        self.import_job_ids.append(import_job_id)
        self._raise_if_configured()

    def publish_recipe_embedding(self, recipe_id: str) -> None:
        self.recipe_ids.append(recipe_id)
        self._raise_if_configured()

    def publish_account_deletion(self, user_id: str) -> None:
        self.user_ids.append(user_id)
        self._raise_if_configured()


class FakeSqsClient:
    def __init__(
        self,
        *,
        response: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response if response is not None else {"MessageId": "message-1"}
        self.error = error
        self.calls: list[dict[str, str]] = []

    def send_message(
        self,
        *,
        QueueUrl: str,
        MessageBody: str,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "QueueUrl": QueueUrl,
                "MessageBody": MessageBody,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


def create_sqs_publisher(client: FakeSqsClient) -> SqsQueuePublisher:
    return SqsQueuePublisher(
        aws_region="eu-west-1",
        imports_queue_url=IMPORTS_QUEUE_URL,
        embeddings_queue_url=EMBEDDINGS_QUEUE_URL,
        account_deletion_queue_url=ACCOUNT_DELETION_QUEUE_URL,
        client=client,
    )


def create_outbox_message(
    session_factory,
    message_type: QueueMessageType,
    entity_id: str,
) -> str:
    with session_factory() as session:
        message = QueueOutboxMessage(
            message_type=message_type,
            entity_id=entity_id,
        )
        session.add(message)
        session.commit()
        return message.id


def configure_dispatch(monkeypatch, session_factory, publisher) -> None:
    monkeypatch.setattr(session_module, "SessionLocal", session_factory)
    monkeypatch.setattr(outbox_module, "get_queue_publisher", lambda: publisher)


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


@pytest.mark.parametrize(
    ("message_type", "entity_id", "published_ids_attribute"),
    [
        (QueueMessageType.IMPORT_JOB, "job-1", "import_job_ids"),
        (
            QueueMessageType.RECIPE_EMBEDDING,
            "missing-recipe-1",
            "recipe_ids",
        ),
        (QueueMessageType.ACCOUNT_DELETION, "user-1", "user_ids"),
    ],
)
def test_dispatch_outbox_message_publishes_entity_id_and_marks_message_published(
    monkeypatch,
    message_type,
    entity_id,
    published_ids_attribute,
):
    session_factory = create_session_factory()
    publisher = StubQueuePublisher()
    configure_dispatch(monkeypatch, session_factory, publisher)
    message_id = create_outbox_message(
        session_factory,
        message_type,
        entity_id,
    )

    assert dispatch_outbox_message(message_id) is True
    assert getattr(publisher, published_ids_attribute) == [entity_id]

    with session_factory() as session:
        message = session.get(QueueOutboxMessage, message_id)
        assert message is not None
        assert message.status is QueueOutboxStatus.PUBLISHED
        assert message.attempt_count == 1
        assert message.last_attempt_at is not None
        assert message.last_error_type is None
        assert message.published_at is not None


def test_dispatch_outbox_message_records_safe_broker_failure_metadata(monkeypatch):
    session_factory = create_session_factory()
    publisher = StubQueuePublisher(RuntimeError("broker unavailable"))
    configure_dispatch(monkeypatch, session_factory, publisher)
    message_id = create_outbox_message(
        session_factory,
        QueueMessageType.IMPORT_JOB,
        "job-1",
    )

    assert dispatch_outbox_message(message_id) is False

    with session_factory() as session:
        message = session.get(QueueOutboxMessage, message_id)
        assert message is not None
        assert message.status is QueueOutboxStatus.PENDING
        assert message.attempt_count == 1
        assert message.last_attempt_at is not None
        assert message.last_error_type == "RuntimeError"
        assert message.published_at is None


def test_dispatch_outbox_message_publishes_import_through_sqs(monkeypatch):
    session_factory = create_session_factory()
    client = FakeSqsClient()
    configure_dispatch(monkeypatch, session_factory, create_sqs_publisher(client))
    message_id = create_outbox_message(
        session_factory,
        QueueMessageType.IMPORT_JOB,
        "job-1",
    )

    assert dispatch_outbox_message(message_id) is True
    assert client.calls == [
        {
            "QueueUrl": IMPORTS_QUEUE_URL,
            "MessageBody": '{"importJobId":"job-1"}',
        }
    ]

    with session_factory() as session:
        message = session.get(QueueOutboxMessage, message_id)
        assert message is not None
        assert message.status is QueueOutboxStatus.PUBLISHED
        assert message.attempt_count == 1
        assert message.last_error_type is None
        assert message.published_at is not None


def test_dispatch_outbox_message_records_safe_sqs_failure(monkeypatch):
    session_factory = create_session_factory()
    client = FakeSqsClient(error=RuntimeError("sqs unavailable"))
    configure_dispatch(monkeypatch, session_factory, create_sqs_publisher(client))
    message_id = create_outbox_message(
        session_factory,
        QueueMessageType.IMPORT_JOB,
        "job-1",
    )

    assert dispatch_outbox_message(message_id) is False

    with session_factory() as session:
        message = session.get(QueueOutboxMessage, message_id)
        assert message is not None
        assert message.status is QueueOutboxStatus.PENDING
        assert message.attempt_count == 1
        assert message.last_error_type == "RuntimeError"
        assert message.published_at is None
        persisted_values = {column.key: getattr(message, column.key) for column in QueueOutboxMessage.__mapper__.column_attrs}
        assert "sqs unavailable" not in repr(persisted_values)


def test_dispatch_outbox_message_records_missing_sqs_message_id(monkeypatch):
    session_factory = create_session_factory()
    client = FakeSqsClient(response={})
    configure_dispatch(monkeypatch, session_factory, create_sqs_publisher(client))
    message_id = create_outbox_message(
        session_factory,
        QueueMessageType.IMPORT_JOB,
        "job-1",
    )

    assert dispatch_outbox_message(message_id) is False

    with session_factory() as session:
        message = session.get(QueueOutboxMessage, message_id)
        assert message is not None
        assert message.status is QueueOutboxStatus.PENDING
        assert message.attempt_count == 1
        assert message.last_error_type == "RuntimeError"
        assert message.published_at is None


def test_dispatch_outbox_message_is_noop_for_published_message(monkeypatch):
    session_factory = create_session_factory()
    publisher = StubQueuePublisher()
    configure_dispatch(monkeypatch, session_factory, publisher)
    message_id = create_outbox_message(
        session_factory,
        QueueMessageType.IMPORT_JOB,
        "job-1",
    )
    assert dispatch_outbox_message(message_id) is True
    publisher.import_job_ids.clear()

    assert dispatch_outbox_message(message_id) is True
    assert publisher.import_job_ids == []


def test_dispatch_outbox_message_returns_false_for_missing_message(monkeypatch):
    session_factory = create_session_factory()
    publisher = StubQueuePublisher()
    configure_dispatch(monkeypatch, session_factory, publisher)

    assert dispatch_outbox_message("missing-message") is False
    assert publisher.import_job_ids == []
    assert publisher.recipe_ids == []
    assert publisher.user_ids == []


def test_embedding_publish_records_one_enqueued_event(monkeypatch):
    session_factory = create_session_factory()
    publisher = StubQueuePublisher()
    configure_dispatch(monkeypatch, session_factory, publisher)

    with session_factory() as session:
        user = User(id="owner-1", email="owner@example.test")
        recipe = Recipe(
            id="recipe-1",
            owner=user,
            title="Soup",
            instructions=["Heat water"],
        )
        recipe.embedding = RecipeEmbedding(
            model="test-embedding",
            status=RecipeEmbeddingStatus.STALE,
        )
        session.add(recipe)
        session.commit()

    message_id = create_outbox_message(
        session_factory,
        QueueMessageType.RECIPE_EMBEDDING,
        "recipe-1",
    )

    assert dispatch_outbox_message(message_id) is True
    assert dispatch_outbox_message(message_id) is True

    with session_factory() as session:
        events = (
            session.query(RecipeEmbeddingEvent)
            .filter(
                RecipeEmbeddingEvent.recipe_id == "recipe-1",
                RecipeEmbeddingEvent.event_type == RecipeEmbeddingEventType.ENQUEUED,
            )
            .all()
        )
        assert len(events) == 1
        assert events[0].owner_id == "owner-1"
        assert events[0].payload == {
            "taskName": "embed_recipe",
            "recipeId": "recipe-1",
        }


def test_post_send_persistence_failure_leaves_message_recoverable(
    monkeypatch,
):
    session_factory = create_session_factory()
    publisher = StubQueuePublisher()
    configure_dispatch(monkeypatch, session_factory, publisher)
    message_id = create_outbox_message(
        session_factory,
        QueueMessageType.IMPORT_JOB,
        "job-1",
    )
    record_publish_success = outbox_module._record_publish_success

    def fail_success_persistence(*_args, **_kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        outbox_module,
        "_record_publish_success",
        fail_success_persistence,
    )
    assert dispatch_outbox_message(message_id) is False

    with session_factory() as session:
        message = session.get(QueueOutboxMessage, message_id)
        assert message is not None
        assert message.status is QueueOutboxStatus.PENDING

    monkeypatch.setattr(
        outbox_module,
        "_record_publish_success",
        record_publish_success,
    )
    assert dispatch_outbox_message(message_id) is True
    assert publisher.import_job_ids == ["job-1", "job-1"]


def test_get_outbox_message_can_lock_row_for_transition():
    class RecordingSession:
        statement = None

        def scalar(self, statement):
            self.statement = statement
            return None

    session = RecordingSession()

    assert (
        get_outbox_message(
            session,
            "message-1",
            for_update=True,
        )
        is None
    )
    compiled = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in compiled
