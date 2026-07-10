from contextlib import contextmanager
from dataclasses import FrozenInstanceError

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.init import ensure_default_user
from app.embeddings.input import build_recipe_embedding_input
from app.embeddings.processing import process_recipe_embedding, start_recipe_embedding
from app.models import (
    Ingredient,
    Recipe,
    RecipeEmbedding,
    RecipeEmbeddingEventType,
    RecipeEmbeddingStatus,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    RecipeReviewFlagType,
)


class StaticEmbeddingProvider:
    model = "test-embedding"

    def __init__(self, active_session_count: dict[str, int] | None = None):
        self.active_session_count = active_session_count

    def embed(self, text: str) -> list[float]:
        if self.active_session_count is not None:
            assert self.active_session_count["value"] == 0
        return [0.1, 0.2, 0.3]


class FailingEmbeddingProvider:
    model = "test-embedding"

    def embed(self, text: str) -> list[float]:
        raise RuntimeError("embedding failed")


class MutatingEmbeddingProvider:
    model = "test-embedding"

    def __init__(self, session_factory, recipe_id: str):
        self.session_factory = session_factory
        self.recipe_id = recipe_id

    def embed(self, text: str) -> list[float]:
        with self.session_factory() as session:
            recipe = session.get(Recipe, self.recipe_id)
            assert recipe is not None
            recipe.title = "Changed soup"
            session.commit()
        return [0.1, 0.2, 0.3]


def create_session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_recipe(session, *, with_open_flag: bool = False) -> Recipe:
    user = ensure_default_user(session)
    recipe = Recipe(owner_id=user.id, title="Soup", instructions=["Heat water"])
    recipe.ingredients.append(Ingredient(name="Water", search_name="water", position=0))
    if with_open_flag:
        recipe.review_flags.append(
            RecipeReviewFlag(
                owner_id=user.id,
                type=RecipeReviewFlagType.CONTENT_WARNING,
                status=RecipeReviewFlagStatus.OPEN,
                reason_code="CONTENT_WARNING",
                message="Needs review.",
            )
        )
    session.add(recipe)
    session.commit()
    return recipe


def tracked_db_session(session_factory, active_session_count: dict[str, int]):
    @contextmanager
    def manager():
        session = session_factory()
        active_session_count["value"] += 1
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            active_session_count["value"] -= 1
            session.close()

    return manager


def test_start_embedding_returns_frozen_running_context():
    SessionLocal = create_session_factory()
    with SessionLocal() as session:
        recipe = create_recipe(session)

        context = start_recipe_embedding(
            session,
            recipe.id,
            provider_name="test",
            model="test-embedding",
        )

        assert context is not None
        assert context.recipe_id == recipe.id
        assert context.owner_id == recipe.owner_id
        assert context.provider_name == "test"
        assert context.model == "test-embedding"
        assert context.embedding_input == build_recipe_embedding_input(recipe)
        embedding = session.get(RecipeEmbedding, recipe.id)
        assert embedding is not None
        assert embedding.status is RecipeEmbeddingStatus.RUNNING
        assert [event.event_type for event in embedding.events] == [RecipeEmbeddingEventType.STARTED]
        with pytest.raises(FrozenInstanceError):
            context.model = "changed"


def test_start_embedding_returns_none_for_missing_recipe():
    SessionLocal = create_session_factory()
    with SessionLocal() as session:
        assert (
            start_recipe_embedding(
                session,
                "missing",
                provider_name="test",
                model="test-embedding",
            )
            is None
        )


def test_start_embedding_skips_recipe_with_open_flags(monkeypatch):
    SessionLocal = create_session_factory()
    monkeypatch.setattr("app.embeddings.planning.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
    with SessionLocal() as session:
        recipe = create_recipe(session, with_open_flag=True)

        context = start_recipe_embedding(
            session,
            recipe.id,
            provider_name="test",
            model="test-embedding",
        )

        assert context is None
        embedding = session.get(RecipeEmbedding, recipe.id)
        assert embedding is not None
        assert embedding.status is RecipeEmbeddingStatus.SKIPPED_DUE_TO_FLAGS
        assert [event.event_type for event in embedding.events] == [RecipeEmbeddingEventType.SKIPPED_DUE_TO_FLAGS]


def test_start_embedding_records_worker_already_ready_noop():
    SessionLocal = create_session_factory()
    with SessionLocal() as session:
        recipe = create_recipe(session)
        embedding_input = build_recipe_embedding_input(recipe)
        embedding = RecipeEmbedding(
            recipe_id=recipe.id,
            model="test-embedding",
            input_hash=embedding_input.input_hash,
            status=RecipeEmbeddingStatus.READY,
        )
        session.add(embedding)
        session.commit()

        context = start_recipe_embedding(
            session,
            recipe.id,
            provider_name="test",
            model="test-embedding",
        )

        assert context is None
        assert embedding.status is RecipeEmbeddingStatus.READY
        assert [event.event_type for event in embedding.events] == [RecipeEmbeddingEventType.ALREADY_READY]


def test_process_embedding_calls_provider_without_open_session_and_saves_vector(monkeypatch):
    SessionLocal = create_session_factory()
    with SessionLocal() as session:
        recipe_id = create_recipe(session).id
    active_session_count = {"value": 0}
    provider = StaticEmbeddingProvider(active_session_count)
    monkeypatch.setattr("app.embeddings.processing.db_session", tracked_db_session(SessionLocal, active_session_count))
    monkeypatch.setattr("app.embeddings.processing.get_embedding_provider", lambda: ("test", provider))

    process_recipe_embedding(recipe_id)

    with SessionLocal() as session:
        embedding = session.get(RecipeEmbedding, recipe_id)
        assert embedding is not None
        assert embedding.status is RecipeEmbeddingStatus.READY
        assert embedding.embedding == [0.1, 0.2, 0.3]
        assert [event.event_type for event in embedding.events] == [
            RecipeEmbeddingEventType.STARTED,
            RecipeEmbeddingEventType.PROVIDER_SUCCEEDED,
            RecipeEmbeddingEventType.SAVED,
        ]


def test_process_embedding_persists_failure_in_fresh_session_and_reraises(monkeypatch):
    SessionLocal = create_session_factory()
    with SessionLocal() as session:
        recipe_id = create_recipe(session).id
    monkeypatch.setattr("app.embeddings.processing.db_session", tracked_db_session(SessionLocal, {"value": 0}))
    monkeypatch.setattr(
        "app.embeddings.processing.get_embedding_provider",
        lambda: ("test", FailingEmbeddingProvider()),
    )

    with pytest.raises(RuntimeError, match="embedding failed"):
        process_recipe_embedding(recipe_id)

    with SessionLocal() as session:
        embedding = session.get(RecipeEmbedding, recipe_id)
        assert embedding is not None
        assert embedding.status is RecipeEmbeddingStatus.FAILED
        assert embedding.failed_attempts == 1
        assert embedding.events[-1].event_type is RecipeEmbeddingEventType.FAILED
        assert embedding.events[-1].payload["failedAttempts"] == 1


def test_process_embedding_requeues_when_recipe_changes_during_provider_call(monkeypatch):
    SessionLocal = create_session_factory()
    with SessionLocal() as session:
        recipe = create_recipe(session)
        recipe_id = recipe.id
    enqueued: list[tuple[str, str]] = []
    provider = MutatingEmbeddingProvider(SessionLocal, recipe_id)
    monkeypatch.setattr("app.embeddings.processing.db_session", tracked_db_session(SessionLocal, {"value": 0}))
    monkeypatch.setattr("app.embeddings.processing.get_embedding_provider", lambda: ("test", provider))
    monkeypatch.setattr(
        "app.embeddings.processing.enqueue_recipe_embedding",
        lambda recipe_id, owner_id: enqueued.append((recipe_id, owner_id)) or False,
    )

    process_recipe_embedding(recipe_id)

    with SessionLocal() as session:
        embedding = session.get(RecipeEmbedding, recipe_id)
        assert embedding is not None
        assert embedding.status is RecipeEmbeddingStatus.STALE
        assert enqueued == [(recipe_id, embedding.recipe.owner_id)]
        assert [event.event_type for event in embedding.events] == [
            RecipeEmbeddingEventType.STARTED,
            RecipeEmbeddingEventType.PROVIDER_SUCCEEDED,
            RecipeEmbeddingEventType.STALE_REQUEUED,
        ]
