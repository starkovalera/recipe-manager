from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as session_module
from app.db.base import Base
from app.embeddings import queue as queue_module
from app.embeddings.queue import enqueue_recipe_embedding
from app.local.users import ensure_default_user
from app.models import (
    Recipe,
    RecipeEmbedding,
    RecipeEmbeddingEventType,
    RecipeEmbeddingStatus,
)


class StubQueuePublisher:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.recipe_ids: list[str] = []

    def publish_import_job(self, import_job_id: str) -> None:
        raise AssertionError(f"Unexpected import publication for {import_job_id}")

    def publish_recipe_embedding(self, recipe_id: str) -> None:
        self.recipe_ids.append(recipe_id)
        if self.error is not None:
            raise self.error

    def publish_account_deletion(self, user_id: str) -> None:
        raise AssertionError(f"Unexpected account deletion publication for {user_id}")


def create_session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_stale_embedding(session) -> RecipeEmbedding:
    user = ensure_default_user(session)
    recipe = Recipe(owner_id=user.id, title="Soup", instructions=["Heat water"])
    recipe.embedding = RecipeEmbedding(
        model="test-embedding",
        input_hash="input-hash",
        status=RecipeEmbeddingStatus.STALE,
    )
    session.add(recipe)
    session.commit()
    return recipe.embedding


def test_enqueue_publishes_before_recording_enqueued_event(monkeypatch):
    SessionLocal = create_session_factory()
    monkeypatch.setattr(session_module, "SessionLocal", SessionLocal)
    with SessionLocal() as session:
        embedding = create_stale_embedding(session)
        recipe_id = embedding.recipe_id
        owner_id = embedding.recipe.owner_id
    publisher = StubQueuePublisher()
    monkeypatch.setattr(queue_module, "get_queue_publisher", lambda: publisher, raising=False)

    published = enqueue_recipe_embedding(recipe_id, owner_id)

    assert published is True
    assert publisher.recipe_ids == [recipe_id]
    with SessionLocal() as session:
        embedding = session.get(RecipeEmbedding, recipe_id)
        assert embedding is not None
        assert [event.event_type for event in embedding.events] == [RecipeEmbeddingEventType.ENQUEUED]
        assert embedding.events[0].status_after is RecipeEmbeddingStatus.STALE


def test_enqueue_returns_false_without_event_when_broker_publish_fails(monkeypatch, capsys):
    SessionLocal = create_session_factory()
    monkeypatch.setattr(session_module, "SessionLocal", SessionLocal)
    with SessionLocal() as session:
        embedding = create_stale_embedding(session)
        recipe_id = embedding.recipe_id
        owner_id = embedding.recipe.owner_id

    publisher = StubQueuePublisher(RuntimeError("broker unavailable"))
    monkeypatch.setattr(queue_module, "get_queue_publisher", lambda: publisher, raising=False)
    published = enqueue_recipe_embedding(recipe_id, owner_id)

    assert published is False
    assert publisher.recipe_ids == [recipe_id]
    with SessionLocal() as session:
        embedding = session.get(RecipeEmbedding, recipe_id)
        assert embedding is not None
        assert embedding.status is RecipeEmbeddingStatus.STALE
        assert embedding.events == []

    message = next(line for line in capsys.readouterr().out.splitlines() if "Embedding task publish failed" in line)
    assert " recipes.embeddings Embedding task publish failed {" in message
    assert f'"recipe_id": "{recipe_id}"' in message
    assert f'"owner_id": "{owner_id}"' in message
    assert "[recipes.embeddings]" not in message


def test_enqueue_returns_true_when_event_persistence_fails_after_publish(monkeypatch):
    publisher = StubQueuePublisher()
    monkeypatch.setattr(queue_module, "get_queue_publisher", lambda: publisher, raising=False)

    @contextmanager
    def failing_db_session():
        raise RuntimeError("event persistence failed")
        yield

    monkeypatch.setattr("app.embeddings.queue.db_session", failing_db_session)

    published = enqueue_recipe_embedding("recipe-1", "owner-1")

    assert published is True
    assert publisher.recipe_ids == ["recipe-1"]
