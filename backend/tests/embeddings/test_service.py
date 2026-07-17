from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.embeddings.service import retry_recipe_embedding
from app.local.users import ensure_default_user
from app.models import (
    Ingredient,
    QueueOutboxMessage,
    Recipe,
    RecipeEmbedding,
    RecipeEmbeddingEventType,
    RecipeEmbeddingStatus,
)
from app.queueing.constants import QueueOutboxStatus


class StaticEmbeddingProvider:
    model = "test-embedding"

    def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


def session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_recipe(session) -> Recipe:
    user = ensure_default_user(session)
    recipe = Recipe(owner_id=user.id, title="Soup", instructions=["Heat water"])
    recipe.ingredients.append(Ingredient(name="Water", search_name="water", position=0))
    session.add(recipe)
    session.commit()
    return recipe


def test_retry_embedding_commits_and_dispatches_outbox_when_recipe_has_no_open_flags(monkeypatch):
    SessionLocal = session_factory()
    dispatched_message_ids: list[str] = []
    with SessionLocal() as session:
        monkeypatch.setattr("app.embeddings.service.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        monkeypatch.setattr("app.embeddings.planning.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        monkeypatch.setattr(
            "app.embeddings.service.dispatch_outbox_message",
            lambda message_id: dispatched_message_ids.append(message_id) or True,
            raising=False,
        )
        recipe = create_recipe(session)

        embedding = retry_recipe_embedding(session, recipe.id, recipe.owner_id)

        assert embedding.status is RecipeEmbeddingStatus.STALE
        assert session.get(RecipeEmbedding, recipe.id) is not None
        assert len(dispatched_message_ids) == 1
        outbox_message = session.get(QueueOutboxMessage, dispatched_message_ids[0])
        assert outbox_message is not None
        assert outbox_message.entity_id == recipe.id
        assert outbox_message.status is QueueOutboxStatus.PENDING
        assert [event.event_type for event in embedding.events] == [
            RecipeEmbeddingEventType.RETRY_REQUESTED,
            RecipeEmbeddingEventType.SCHEDULED,
        ]


def test_retry_embedding_succeeds_when_outbox_dispatch_fails(monkeypatch):
    SessionLocal = session_factory()
    with SessionLocal() as session:
        monkeypatch.setattr("app.embeddings.service.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        monkeypatch.setattr("app.embeddings.planning.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        monkeypatch.setattr("app.embeddings.service.dispatch_outbox_message", lambda _message_id: False, raising=False)
        recipe = create_recipe(session)

        embedding = retry_recipe_embedding(session, recipe.id, recipe.owner_id)

        assert embedding.status is RecipeEmbeddingStatus.STALE
        assert [event.event_type for event in embedding.events] == [
            RecipeEmbeddingEventType.RETRY_REQUESTED,
            RecipeEmbeddingEventType.SCHEDULED,
        ]
