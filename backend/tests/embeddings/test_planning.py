from dataclasses import FrozenInstanceError

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.init import ensure_default_user
from app.embeddings.input import build_recipe_embedding_input
from app.embeddings.planning import prepare_recipe_embedding
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

    def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def create_recipe(session: Session, *, open_flag_count: int = 0) -> Recipe:
    user = ensure_default_user(session)
    recipe = Recipe(owner_id=user.id, title="Soup", instructions=["Heat water"])
    recipe.ingredients.append(Ingredient(name="Water", search_name="water", position=0))
    for _ in range(open_flag_count):
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


def test_prepare_embedding_skips_recipe_with_open_flags(monkeypatch):
    with create_session() as session:
        monkeypatch.setattr("app.embeddings.planning.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        recipe = create_recipe(session, open_flag_count=2)

        plan = prepare_recipe_embedding(session, recipe)

        assert plan.enqueue is False
        assert plan.embedding.status is RecipeEmbeddingStatus.SKIPPED_DUE_TO_FLAGS
        assert plan.embedding.events[0].event_type is RecipeEmbeddingEventType.SKIPPED_DUE_TO_FLAGS
        assert plan.embedding.events[0].payload == {"reason": "open_review_flags", "openFlagCount": 2}


def test_prepare_embedding_creates_missing_embedding_and_schedules(monkeypatch):
    with create_session() as session:
        monkeypatch.setattr("app.embeddings.planning.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        recipe = create_recipe(session)

        plan = prepare_recipe_embedding(session, recipe)

        assert plan.enqueue is True
        assert plan.embedding is session.get(RecipeEmbedding, recipe.id)
        assert plan.embedding.status is RecipeEmbeddingStatus.STALE
        assert plan.embedding.events[0].event_type is RecipeEmbeddingEventType.SCHEDULED


def test_prepare_embedding_keeps_current_ready_embedding_without_scheduler_event(monkeypatch):
    with create_session() as session:
        monkeypatch.setattr("app.embeddings.planning.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        recipe = create_recipe(session)
        embedding_input = build_recipe_embedding_input(recipe)
        recipe.embedding = RecipeEmbedding(
            model="test-embedding",
            input_hash=embedding_input.input_hash,
            status=RecipeEmbeddingStatus.READY,
        )
        session.commit()

        plan = prepare_recipe_embedding(session, recipe)

        assert plan.enqueue is False
        assert plan.embedding.status is RecipeEmbeddingStatus.READY
        assert plan.embedding.events == []


def test_prepare_embedding_schedules_when_input_or_model_changed(monkeypatch):
    with create_session() as session:
        monkeypatch.setattr("app.embeddings.planning.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        recipe = create_recipe(session)
        recipe.embedding = RecipeEmbedding(
            model="old-model",
            input_hash="old-hash",
            status=RecipeEmbeddingStatus.READY,
        )
        session.commit()

        plan = prepare_recipe_embedding(session, recipe)

        assert plan.enqueue is True
        assert plan.embedding.status is RecipeEmbeddingStatus.STALE
        assert plan.embedding.model == "test-embedding"
        assert plan.embedding.events[0].event_type is RecipeEmbeddingEventType.SCHEDULED
        assert plan.embedding.events[0].payload["reason"] == "recipe_content_changed"


def test_prepare_embedding_force_schedules_current_ready_embedding(monkeypatch):
    with create_session() as session:
        monkeypatch.setattr("app.embeddings.planning.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        recipe = create_recipe(session)
        embedding_input = build_recipe_embedding_input(recipe)
        recipe.embedding = RecipeEmbedding(
            model="test-embedding",
            input_hash=embedding_input.input_hash,
            status=RecipeEmbeddingStatus.READY,
        )
        session.commit()

        plan = prepare_recipe_embedding(session, recipe, force=True)

        assert plan.enqueue is True
        assert plan.embedding.status is RecipeEmbeddingStatus.STALE
        assert plan.embedding.events[0].payload["reason"] == "manual_retry"
        with pytest.raises(FrozenInstanceError):
            plan.enqueue = False
