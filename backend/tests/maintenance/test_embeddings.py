from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as session_module
from app.db.base import Base
from app.maintenance import embeddings as maintenance_embeddings
from app.maintenance.constants import MaintenanceProcessingDisposition
from app.models import (
    QueueOutboxMessage,
    Recipe,
    RecipeEmbedding,
    RecipeEmbeddingEvent,
    RecipeEmbeddingEventType,
    RecipeEmbeddingStatus,
    RecipeStatus,
    User,
)
from app.queueing.constants import QueueMessageType


def _factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _add_embedding(factory, *, status: RecipeEmbeddingStatus, active: bool = True) -> None:
    stale_at = datetime.now(timezone.utc) - timedelta(hours=2)
    with factory() as session:
        user = User(id="user-1", email="user@example.test")
        recipe = Recipe(id="recipe-1", owner=user, title="Recipe", status=RecipeStatus.ACTIVE if active else RecipeStatus.DELETION_PENDING)
        session.add_all(
            [
                recipe,
                RecipeEmbedding(
                    recipe=recipe,
                    model="model",
                    status=status,
                    failed_attempts=2,
                    error_message="old",
                    last_attempt_at=stale_at if status is RecipeEmbeddingStatus.RUNNING else None,
                    updated_at=stale_at,
                ),
            ]
        )
        session.commit()


def _configure(monkeypatch, factory) -> list[str]:
    dispatched: list[str] = []
    monkeypatch.setattr(session_module, "SessionLocal", factory)
    monkeypatch.setattr(
        maintenance_embeddings,
        "get_settings",
        lambda: SimpleNamespace(maintenance_batch_size=100, stale_embedding_minutes=30),
    )
    monkeypatch.setattr(maintenance_embeddings, "dispatch_outbox_message", lambda value: dispatched.append(value) or True)
    return dispatched


def test_stale_running_embedding_is_requeued_without_provider_call(monkeypatch) -> None:
    factory = _factory()
    _add_embedding(factory, status=RecipeEmbeddingStatus.RUNNING)
    dispatched = _configure(monkeypatch, factory)

    result = maintenance_embeddings.reconcile_stale_embeddings()

    assert result.disposition is MaintenanceProcessingDisposition.COMPLETED
    assert result.changed_count == result.scheduled_count == 1
    assert len(dispatched) == 1
    with factory() as session:
        embedding = session.get(RecipeEmbedding, "recipe-1")
        assert embedding.status is RecipeEmbeddingStatus.STALE
        assert embedding.error_message is None
        assert embedding.failed_attempts == 2
        event = session.query(RecipeEmbeddingEvent).one()
        assert event.event_type is RecipeEmbeddingEventType.STALE_REQUEUED
        assert event.payload == {"reason": "maintenance_stale_recovery"}


def test_stale_embedding_with_pending_intent_is_not_duplicated(monkeypatch) -> None:
    factory = _factory()
    _add_embedding(factory, status=RecipeEmbeddingStatus.STALE)
    with factory() as session:
        session.add(QueueOutboxMessage(message_type=QueueMessageType.RECIPE_EMBEDDING, entity_id="recipe-1"))
        session.commit()
    _configure(monkeypatch, factory)

    result = maintenance_embeddings.reconcile_stale_embeddings()

    assert result.disposition is MaintenanceProcessingDisposition.NOOP
    with factory() as session:
        assert session.query(QueueOutboxMessage).count() == 1


def test_inactive_recipe_embedding_is_ignored(monkeypatch) -> None:
    factory = _factory()
    _add_embedding(factory, status=RecipeEmbeddingStatus.RUNNING, active=False)
    _configure(monkeypatch, factory)

    assert maintenance_embeddings.reconcile_stale_embeddings().disposition is MaintenanceProcessingDisposition.NOOP
