from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as session_module
from app.db.base import Base
from app.db.init import ensure_default_user
from app.embeddings.queue import enqueue_recipe_embedding
from app.models import (
    Recipe,
    RecipeEmbedding,
    RecipeEmbeddingEventType,
    RecipeEmbeddingStatus,
)


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
    calls: list[str] = []

    def send(received_recipe_id: str) -> None:
        calls.append(f"send:{received_recipe_id}")

    monkeypatch.setattr("app.embeddings.tasks.embed_recipe_task.send", send)

    published = enqueue_recipe_embedding(recipe_id, owner_id)

    assert published is True
    assert calls == [f"send:{recipe_id}"]
    with SessionLocal() as session:
        embedding = session.get(RecipeEmbedding, recipe_id)
        assert embedding is not None
        assert [event.event_type for event in embedding.events] == [RecipeEmbeddingEventType.ENQUEUED]
        assert embedding.events[0].status_after is RecipeEmbeddingStatus.STALE


def test_enqueue_returns_false_without_event_when_broker_publish_fails(monkeypatch):
    SessionLocal = create_session_factory()
    monkeypatch.setattr(session_module, "SessionLocal", SessionLocal)
    with SessionLocal() as session:
        embedding = create_stale_embedding(session)
        recipe_id = embedding.recipe_id
        owner_id = embedding.recipe.owner_id

    def fail_send(recipe_id: str) -> None:
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr("app.embeddings.tasks.embed_recipe_task.send", fail_send)

    published = enqueue_recipe_embedding(recipe_id, owner_id)

    assert published is False
    with SessionLocal() as session:
        embedding = session.get(RecipeEmbedding, recipe_id)
        assert embedding is not None
        assert embedding.status is RecipeEmbeddingStatus.STALE
        assert embedding.events == []


def test_enqueue_returns_true_when_event_persistence_fails_after_publish(monkeypatch):
    published_recipe_ids: list[str] = []
    monkeypatch.setattr("app.embeddings.tasks.embed_recipe_task.send", published_recipe_ids.append)

    @contextmanager
    def failing_db_session():
        raise RuntimeError("event persistence failed")
        yield

    monkeypatch.setattr("app.embeddings.queue.db_session", failing_db_session)

    published = enqueue_recipe_embedding("recipe-1", "owner-1")

    assert published is True
    assert published_recipe_ids == ["recipe-1"]
