from contextlib import contextmanager
from dataclasses import FrozenInstanceError

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.embeddings.input import build_recipe_embedding_input
from app.embeddings.outcomes import EmbeddingProcessingDisposition, EmbeddingProcessingResult
from app.embeddings.processing import EmbeddingStartResult, process_recipe_embedding, start_recipe_embedding
from app.local.users import ensure_default_user
from app.models import (
    Ingredient,
    QueueOutboxMessage,
    Recipe,
    RecipeEmbedding,
    RecipeEmbeddingEventType,
    RecipeEmbeddingStatus,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    RecipeReviewFlagType,
)
from app.queueing.constants import QueueOutboxStatus


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


def test_embedding_processing_outcomes_are_explicit_and_frozen() -> None:
    assert [disposition.value for disposition in EmbeddingProcessingDisposition] == [
        "SUCCEEDED",
        "NOOP",
        "REQUEUED",
        "BUSY",
        "RETRYABLE_FAILURE",
    ]
    result = EmbeddingProcessingResult(
        recipe_id="recipe-1",
        disposition=EmbeddingProcessingDisposition.SUCCEEDED,
    )
    assert result.failed_attempts is None
    with pytest.raises(FrozenInstanceError):
        result.recipe_id = "recipe-2"


def test_start_embedding_returns_frozen_running_context():
    SessionLocal = create_session_factory()
    with SessionLocal() as session:
        recipe = create_recipe(session)

        start_result = start_recipe_embedding(
            session,
            recipe.id,
            provider_name="test",
            model="test-embedding",
        )

        assert start_result.result is None
        context = start_result.context
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
        start_result = start_recipe_embedding(
            session,
            "missing",
            provider_name="test",
            model="test-embedding",
        )
        assert start_result.context is None
        assert start_result.result == EmbeddingProcessingResult(
            recipe_id="missing",
            disposition=EmbeddingProcessingDisposition.NOOP,
        )


def test_start_embedding_skips_recipe_with_open_flags(monkeypatch):
    SessionLocal = create_session_factory()
    monkeypatch.setattr("app.embeddings.planning.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))
    with SessionLocal() as session:
        recipe = create_recipe(session, with_open_flag=True)

        start_result = start_recipe_embedding(
            session,
            recipe.id,
            provider_name="test",
            model="test-embedding",
        )

        assert start_result.context is None
        assert start_result.result == EmbeddingProcessingResult(
            recipe_id=recipe.id,
            disposition=EmbeddingProcessingDisposition.NOOP,
        )
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

        start_result = start_recipe_embedding(
            session,
            recipe.id,
            provider_name="test",
            model="test-embedding",
        )

        assert start_result.context is None
        assert start_result.result == EmbeddingProcessingResult(
            recipe_id=recipe.id,
            disposition=EmbeddingProcessingDisposition.NOOP,
        )
        assert embedding.status is RecipeEmbeddingStatus.READY
        assert [event.event_type for event in embedding.events] == [RecipeEmbeddingEventType.ALREADY_READY]


def test_start_embedding_returns_busy_without_mutating_running_embedding():
    SessionLocal = create_session_factory()
    with SessionLocal() as session:
        recipe = create_recipe(session)
        embedding = RecipeEmbedding(
            recipe_id=recipe.id,
            model="test-embedding",
            input_hash="existing-hash",
            status=RecipeEmbeddingStatus.RUNNING,
        )
        session.add(embedding)
        session.commit()

        start_result = start_recipe_embedding(
            session,
            recipe.id,
            provider_name="test",
            model="test-embedding",
        )

        assert start_result.context is None
        assert start_result.result == EmbeddingProcessingResult(
            recipe_id=recipe.id,
            disposition=EmbeddingProcessingDisposition.BUSY,
        )
        assert embedding.input_hash == "existing-hash"
        assert embedding.events == []


@pytest.mark.parametrize(
    ("status", "model", "input_hash", "failed_attempts"),
    [
        (RecipeEmbeddingStatus.FAILED, "test-embedding", "old-hash", 2),
        (RecipeEmbeddingStatus.STALE, "test-embedding", "old-hash", 0),
        (RecipeEmbeddingStatus.READY, "old-model", "old-hash", 0),
    ],
)
def test_start_embedding_claims_retryable_or_outdated_embedding(
    status: RecipeEmbeddingStatus,
    model: str,
    input_hash: str,
    failed_attempts: int,
):
    SessionLocal = create_session_factory()
    with SessionLocal() as session:
        recipe = create_recipe(session)
        embedding = RecipeEmbedding(
            recipe_id=recipe.id,
            model=model,
            input_hash=input_hash,
            status=status,
            failed_attempts=failed_attempts,
        )
        session.add(embedding)
        session.commit()

        start_result = start_recipe_embedding(
            session,
            recipe.id,
            provider_name="test",
            model="test-embedding",
        )

        assert start_result.result is None
        assert start_result.context is not None
        assert embedding.status is RecipeEmbeddingStatus.RUNNING
        assert embedding.failed_attempts == failed_attempts
        assert [event.event_type for event in embedding.events] == [RecipeEmbeddingEventType.STARTED]


def test_embedding_start_result_requires_exactly_one_value() -> None:
    result = EmbeddingProcessingResult(
        recipe_id="recipe-1",
        disposition=EmbeddingProcessingDisposition.NOOP,
    )
    with pytest.raises(ValueError, match="exactly one"):
        EmbeddingStartResult(context=None, result=None)
    with pytest.raises(ValueError, match="exactly one"):
        EmbeddingStartResult(context=object(), result=result)


def test_process_embedding_calls_provider_without_open_session_and_saves_vector(monkeypatch):
    SessionLocal = create_session_factory()
    with SessionLocal() as session:
        recipe_id = create_recipe(session).id
    active_session_count = {"value": 0}
    provider = StaticEmbeddingProvider(active_session_count)
    monkeypatch.setattr("app.embeddings.processing.db_session", tracked_db_session(SessionLocal, active_session_count))
    monkeypatch.setattr("app.embeddings.processing.get_embedding_provider", lambda: ("test", provider))

    result = process_recipe_embedding(recipe_id)

    assert result == EmbeddingProcessingResult(
        recipe_id=recipe_id,
        disposition=EmbeddingProcessingDisposition.SUCCEEDED,
    )

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


def test_process_embedding_persists_failure_and_returns_retryable_result(monkeypatch, capsys):
    SessionLocal = create_session_factory()
    with SessionLocal() as session:
        recipe_id = create_recipe(session).id
    monkeypatch.setattr("app.embeddings.processing.db_session", tracked_db_session(SessionLocal, {"value": 0}))
    monkeypatch.setattr(
        "app.embeddings.processing.get_embedding_provider",
        lambda: ("test", FailingEmbeddingProvider()),
    )
    result = process_recipe_embedding(recipe_id)

    assert result == EmbeddingProcessingResult(
        recipe_id=recipe_id,
        disposition=EmbeddingProcessingDisposition.RETRYABLE_FAILURE,
        failed_attempts=1,
    )

    with SessionLocal() as session:
        embedding = session.get(RecipeEmbedding, recipe_id)
        assert embedding is not None
        assert embedding.status is RecipeEmbeddingStatus.FAILED
        assert embedding.failed_attempts == 1
        assert embedding.events[-1].event_type is RecipeEmbeddingEventType.FAILED
        assert embedding.events[-1].payload["failedAttempts"] == 1

    message = next(line for line in capsys.readouterr().out.splitlines() if "Embedding provider failed" in line)
    assert " recipes.embeddings Embedding provider failed {" in message
    assert '"recipe_id"' in message
    assert '"owner_id"' in message
    assert '"provider_name": "test"' in message
    assert '"model": "test-embedding"' in message
    assert '"input_hash"' in message
    assert '"failed_attempts": 1' in message
    assert "[recipes.embeddings]" not in message


def test_process_embedding_requeues_when_recipe_changes_during_provider_call(monkeypatch):
    SessionLocal = create_session_factory()
    with SessionLocal() as session:
        recipe = create_recipe(session)
        recipe_id = recipe.id
    dispatched_message_ids: list[str] = []
    provider = MutatingEmbeddingProvider(SessionLocal, recipe_id)
    monkeypatch.setattr("app.embeddings.processing.db_session", tracked_db_session(SessionLocal, {"value": 0}))
    monkeypatch.setattr("app.embeddings.processing.get_embedding_provider", lambda: ("test", provider))
    monkeypatch.setattr(
        "app.embeddings.processing.dispatch_outbox_message",
        lambda message_id: dispatched_message_ids.append(message_id) or False,
        raising=False,
    )

    result = process_recipe_embedding(recipe_id)

    assert result == EmbeddingProcessingResult(
        recipe_id=recipe_id,
        disposition=EmbeddingProcessingDisposition.REQUEUED,
    )

    with SessionLocal() as session:
        embedding = session.get(RecipeEmbedding, recipe_id)
        assert embedding is not None
        assert embedding.status is RecipeEmbeddingStatus.STALE
        assert len(dispatched_message_ids) == 1
        outbox_message = session.get(QueueOutboxMessage, dispatched_message_ids[0])
        assert outbox_message is not None
        assert outbox_message.entity_id == recipe_id
        assert outbox_message.status is QueueOutboxStatus.PENDING
        assert [event.event_type for event in embedding.events] == [
            RecipeEmbeddingEventType.STARTED,
            RecipeEmbeddingEventType.PROVIDER_SUCCEEDED,
            RecipeEmbeddingEventType.STALE_REQUEUED,
        ]


@pytest.mark.parametrize(
    ("recipe_exists", "embedding_status", "expected_disposition"),
    [
        (False, None, EmbeddingProcessingDisposition.NOOP),
        (True, RecipeEmbeddingStatus.RUNNING, EmbeddingProcessingDisposition.BUSY),
    ],
)
def test_process_embedding_returns_without_provider_for_noop_or_busy(
    monkeypatch,
    recipe_exists: bool,
    embedding_status: RecipeEmbeddingStatus | None,
    expected_disposition: EmbeddingProcessingDisposition,
):
    SessionLocal = create_session_factory()
    recipe_id = "missing"
    if recipe_exists:
        with SessionLocal() as session:
            recipe = create_recipe(session)
            recipe_id = recipe.id
            session.add(
                RecipeEmbedding(
                    recipe_id=recipe.id,
                    model="test-embedding",
                    input_hash="existing-hash",
                    status=embedding_status,
                )
            )
            session.commit()

    class ProviderMustNotRun:
        model = "test-embedding"

        def embed(self, text: str) -> list[float]:
            raise AssertionError("provider must not be called")

    monkeypatch.setattr("app.embeddings.processing.db_session", tracked_db_session(SessionLocal, {"value": 0}))
    monkeypatch.setattr("app.embeddings.processing.get_embedding_provider", lambda: ("test", ProviderMustNotRun()))

    result = process_recipe_embedding(recipe_id)

    assert result == EmbeddingProcessingResult(
        recipe_id=recipe_id,
        disposition=expected_disposition,
    )


def test_failed_embedding_can_be_claimed_and_processed_again(monkeypatch):
    SessionLocal = create_session_factory()
    with SessionLocal() as session:
        recipe = create_recipe(session)
        recipe_id = recipe.id
        session.add(
            RecipeEmbedding(
                recipe_id=recipe.id,
                model="test-embedding",
                input_hash="old-hash",
                status=RecipeEmbeddingStatus.FAILED,
                failed_attempts=2,
            )
        )
        session.commit()

    monkeypatch.setattr("app.embeddings.processing.db_session", tracked_db_session(SessionLocal, {"value": 0}))
    monkeypatch.setattr("app.embeddings.processing.get_embedding_provider", lambda: ("test", StaticEmbeddingProvider()))

    result = process_recipe_embedding(recipe_id)

    assert result.disposition is EmbeddingProcessingDisposition.SUCCEEDED
    with SessionLocal() as session:
        embedding = session.get(RecipeEmbedding, recipe_id)
        assert embedding is not None
        assert embedding.status is RecipeEmbeddingStatus.READY
        assert embedding.failed_attempts == 2
