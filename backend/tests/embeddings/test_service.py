from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.init import ensure_default_user
from app.embeddings.input import build_recipe_embedding_input
from app.embeddings.service import process_recipe_embedding, retry_recipe_embedding
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


def session_factory():
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


def test_process_embedding_uses_planning_skip_for_open_flags(monkeypatch):
    SessionLocal = session_factory()
    with SessionLocal() as session:
        monkeypatch.setattr("app.embeddings.planning.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        recipe = create_recipe(session, with_open_flag=True)

        process_recipe_embedding(session, recipe.id)

        embedding = session.get(RecipeEmbedding, recipe.id)
        assert embedding is not None
        assert embedding.status is RecipeEmbeddingStatus.SKIPPED_DUE_TO_FLAGS
        assert [event.event_type for event in embedding.events] == [RecipeEmbeddingEventType.SKIPPED_DUE_TO_FLAGS]


def test_retry_embedding_commits_and_enqueues_when_recipe_has_no_open_flags(monkeypatch):
    SessionLocal = session_factory()
    enqueued: list[str] = []
    with SessionLocal() as session:
        monkeypatch.setattr("app.embeddings.service.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        monkeypatch.setattr("app.embeddings.planning.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        monkeypatch.setattr("app.embeddings.service.enqueue_recipe_embedding", enqueued.append)
        recipe = create_recipe(session)

        embedding = retry_recipe_embedding(session, recipe.id, recipe.owner_id)

        assert embedding.status is RecipeEmbeddingStatus.STALE
        assert session.get(RecipeEmbedding, recipe.id) is not None
        assert enqueued == [recipe.id]
        assert [event.event_type for event in embedding.events] == [
            RecipeEmbeddingEventType.RETRY_REQUESTED,
            RecipeEmbeddingEventType.SCHEDULED,
            RecipeEmbeddingEventType.ENQUEUED,
        ]


def test_process_embedding_saves_ready_vector(monkeypatch):
    SessionLocal = session_factory()
    with SessionLocal() as session:
        monkeypatch.setattr("app.embeddings.service.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        recipe = create_recipe(session)

        process_recipe_embedding(session, recipe.id)
        session.refresh(recipe)

        assert recipe.embedding is not None
        assert recipe.embedding.status is RecipeEmbeddingStatus.READY
        assert recipe.embedding.embedding == [0.1, 0.2, 0.3]
        assert [event.event_type for event in recipe.embedding.events] == [
            RecipeEmbeddingEventType.STARTED,
            RecipeEmbeddingEventType.PROVIDER_SUCCEEDED,
            RecipeEmbeddingEventType.SAVED,
        ]


def test_process_embedding_records_already_ready_noop(monkeypatch):
    SessionLocal = session_factory()
    with SessionLocal() as session:
        monkeypatch.setattr("app.embeddings.service.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
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

        process_recipe_embedding(session, recipe.id)
        session.refresh(embedding)

        assert embedding.status is RecipeEmbeddingStatus.READY
        assert embedding.events[-1].event_type is RecipeEmbeddingEventType.ALREADY_READY


def test_process_embedding_records_provider_failure(monkeypatch):
    SessionLocal = session_factory()
    with SessionLocal() as session:
        monkeypatch.setattr("app.embeddings.service.get_embedding_provider", lambda: ("test", FailingEmbeddingProvider()))
        recipe = create_recipe(session)

        try:
            process_recipe_embedding(session, recipe.id)
        except RuntimeError:
            pass

        embedding = session.get(RecipeEmbedding, recipe.id)
        assert embedding is not None
        assert embedding.status is RecipeEmbeddingStatus.FAILED
        assert embedding.events[-1].event_type is RecipeEmbeddingEventType.FAILED
        assert embedding.events[-1].payload["failedAttempts"] == 1


def test_process_embedding_records_stale_requeue(monkeypatch):
    SessionLocal = session_factory()
    enqueued: list[str] = []
    with SessionLocal() as session:
        recipe = create_recipe(session)
        provider = MutatingEmbeddingProvider(SessionLocal, recipe.id)
        monkeypatch.setattr("app.embeddings.service.get_embedding_provider", lambda: ("test", provider))
        monkeypatch.setattr("app.embeddings.service.enqueue_recipe_embedding", enqueued.append)

        process_recipe_embedding(session, recipe.id)

        embedding = session.get(RecipeEmbedding, recipe.id)
        assert embedding is not None
        assert embedding.status is RecipeEmbeddingStatus.STALE
        assert enqueued == [recipe.id]
        assert [event.event_type for event in embedding.events] == [
            RecipeEmbeddingEventType.STARTED,
            RecipeEmbeddingEventType.PROVIDER_SUCCEEDED,
            RecipeEmbeddingEventType.STALE_REQUEUED,
            RecipeEmbeddingEventType.ENQUEUED,
        ]
