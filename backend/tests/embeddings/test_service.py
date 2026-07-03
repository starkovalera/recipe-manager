from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.init import ensure_default_user
from app.embeddings.events import EmbeddingEventType
from app.embeddings.service import prepare_recipe_embedding, process_recipe_embedding, retry_recipe_embedding
from app.models import (
    Ingredient,
    Recipe,
    RecipeEmbedding,
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


def test_prepare_embedding_skips_recipe_with_open_flags(monkeypatch):
    SessionLocal = session_factory()
    with SessionLocal() as session:
        monkeypatch.setattr("app.embeddings.service.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        recipe = create_recipe(session, with_open_flag=True)

        embedding, should_enqueue = prepare_recipe_embedding(recipe)

        assert should_enqueue is False
        assert embedding.status == RecipeEmbeddingStatus.SKIPPED_DUE_TO_FLAGS.value
        assert [event.event_type for event in embedding.events] == [EmbeddingEventType.SKIPPED_DUE_TO_FLAGS]


def test_retry_embedding_commits_and_enqueues_when_recipe_has_no_open_flags(monkeypatch):
    SessionLocal = session_factory()
    enqueued: list[str] = []
    with SessionLocal() as session:
        monkeypatch.setattr("app.embeddings.service.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        monkeypatch.setattr("app.embeddings.service.enqueue_recipe_embedding", enqueued.append)
        recipe = create_recipe(session)

        embedding = retry_recipe_embedding(session, recipe.id, recipe.owner_id)

        assert embedding.status == RecipeEmbeddingStatus.STALE.value
        assert session.get(RecipeEmbedding, recipe.id) is not None
        assert enqueued == [recipe.id]
        assert [event.event_type for event in embedding.events] == [
            EmbeddingEventType.RETRY_REQUESTED,
            EmbeddingEventType.SCHEDULED,
            EmbeddingEventType.ENQUEUED,
        ]


def test_prepare_embedding_creates_missing_embedding_row(monkeypatch):
    SessionLocal = session_factory()
    with SessionLocal() as session:
        monkeypatch.setattr("app.embeddings.service.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        recipe = create_recipe(session)

        assert recipe.embedding is None

        embedding, should_enqueue = prepare_recipe_embedding(recipe)

        assert should_enqueue is True
        assert embedding.recipe_id == recipe.id
        assert session.get(RecipeEmbedding, recipe.id) is embedding
        assert [event.event_type for event in embedding.events] == [EmbeddingEventType.SCHEDULED]


def test_process_embedding_saves_ready_vector(monkeypatch):
    SessionLocal = session_factory()
    with SessionLocal() as session:
        monkeypatch.setattr("app.embeddings.service.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        recipe = create_recipe(session)

        process_recipe_embedding(session, recipe.id)
        session.refresh(recipe)

        assert recipe.embedding is not None
        assert recipe.embedding.status == RecipeEmbeddingStatus.READY.value
        assert recipe.embedding.embedding == [0.1, 0.2, 0.3]
        assert [event.event_type for event in recipe.embedding.events] == [
            EmbeddingEventType.STARTED,
            EmbeddingEventType.PROVIDER_SUCCEEDED,
            EmbeddingEventType.SAVED,
        ]


def test_process_embedding_records_already_ready_noop(monkeypatch):
    SessionLocal = session_factory()
    with SessionLocal() as session:
        monkeypatch.setattr("app.embeddings.service.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
        recipe = create_recipe(session)
        embedding, _ = prepare_recipe_embedding(recipe)
        embedding.status = RecipeEmbeddingStatus.READY.value
        session.commit()

        process_recipe_embedding(session, recipe.id)
        session.refresh(embedding)

        assert embedding.status == RecipeEmbeddingStatus.READY.value
        assert embedding.events[-1].event_type == EmbeddingEventType.ALREADY_READY


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
        assert embedding.status == RecipeEmbeddingStatus.FAILED.value
        assert embedding.events[-1].event_type == EmbeddingEventType.FAILED
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
        assert embedding.status == RecipeEmbeddingStatus.STALE.value
        assert enqueued == [recipe.id]
        assert [event.event_type for event in embedding.events] == [
            EmbeddingEventType.STARTED,
            EmbeddingEventType.PROVIDER_SUCCEEDED,
            EmbeddingEventType.STALE_REQUEUED,
            EmbeddingEventType.ENQUEUED,
        ]
