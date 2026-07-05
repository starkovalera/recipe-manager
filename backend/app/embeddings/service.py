import logging
from datetime import datetime, timezone
from time import perf_counter

from sqlalchemy.orm import Session, object_session

from app.core.errors import ApiError, ApiErrorCode
from app.core.logging import bind_logger
from app.embeddings.constants import EMBEDDING_LOG_COMPONENT, EMBEDDING_LOG_PREFIX
from app.embeddings.events import EmbeddingEventType, add_embedding_event
from app.embeddings.input import build_recipe_embedding_hash, build_recipe_embedding_input
from app.embeddings.queries import (
    get_or_create_recipe_embedding,
    get_owner_recipe_for_embedding_retry,
    get_recipe_embedding,
    get_recipe_for_embedding,
    has_open_review_flags,
)
from app.embeddings.runtime import get_embedding_provider
from app.models import Recipe, RecipeEmbedding, RecipeEmbeddingStatus, RecipeReviewFlagStatus

logger = logging.getLogger(EMBEDDING_LOG_COMPONENT)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_session(recipe: Recipe) -> Session:
    session = object_session(recipe)
    if session is None:
        raise RuntimeError("Recipe must be attached to a session before embedding state can be updated.")
    return session


def enqueue_recipe_embedding(recipe_id: str) -> None:
    from app.embeddings.tasks import embed_recipe_task

    embed_recipe_task.send(recipe_id)


def enqueue_recipe_embedding_with_event(session: Session, *, embedding: RecipeEmbedding, owner_id: str) -> None:
    enqueue_recipe_embedding(embedding.recipe_id)
    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=owner_id,
        event_type=EmbeddingEventType.ENQUEUED,
        payload={"taskName": "embed_recipe", "recipeId": embedding.recipe_id},
    )


def prepare_recipe_embedding(recipe: Recipe, *, force: bool = False) -> tuple[RecipeEmbedding, bool]:
    session = _require_session(recipe)
    provider_name, provider = get_embedding_provider()
    embedding = get_or_create_recipe_embedding(session, recipe.id, model=provider.model)
    input_hash = build_recipe_embedding_hash(recipe)
    log = bind_logger(logger, component=EMBEDDING_LOG_COMPONENT, recipeId=recipe.id, ownerId=recipe.owner_id, provider=provider_name)

    if any(flag.status == RecipeReviewFlagStatus.OPEN for flag in recipe.review_flags):
        embedding.model = provider.model
        embedding.input_hash = input_hash
        embedding.status = RecipeEmbeddingStatus.SKIPPED_DUE_TO_FLAGS.value
        embedding.error_message = None
        add_embedding_event(
            session,
            embedding=embedding,
            owner_id=recipe.owner_id,
            event_type=EmbeddingEventType.SKIPPED_DUE_TO_FLAGS,
            payload={
                "reason": "open_review_flags",
                "openFlagCount": sum(1 for flag in recipe.review_flags if flag.status == RecipeReviewFlagStatus.OPEN),
            },
        )
        log.info(f"{EMBEDDING_LOG_PREFIX} Embedding skipped due to open review flags")
        return embedding, False

    if not force and embedding.status == RecipeEmbeddingStatus.READY.value and embedding.input_hash == input_hash and embedding.model == provider.model:
        log.info(f"{EMBEDDING_LOG_PREFIX} Embedding already ready")
        return embedding, False

    embedding.model = provider.model
    embedding.input_hash = input_hash
    embedding.status = RecipeEmbeddingStatus.STALE.value
    embedding.error_message = None
    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=recipe.owner_id,
        event_type=EmbeddingEventType.SCHEDULED,
        payload={"reason": "manual_retry" if force else "recipe_content_changed", "model": provider.model},
    )
    log.info(f"{EMBEDDING_LOG_PREFIX} Embedding task planned", force=force)
    return embedding, True


def skip_recipe_embedding_due_to_flags(session: Session, recipe_id: str) -> RecipeEmbedding | None:
    recipe = get_recipe_for_embedding(session, recipe_id)
    if recipe is None:
        return None
    _, provider = get_embedding_provider()
    embedding = get_or_create_recipe_embedding(session, recipe.id, model=provider.model)
    embedding.model = provider.model
    embedding.input_hash = build_recipe_embedding_hash(recipe)
    embedding.status = RecipeEmbeddingStatus.SKIPPED_DUE_TO_FLAGS.value
    embedding.error_message = None
    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=recipe.owner_id,
        event_type=EmbeddingEventType.SKIPPED_DUE_TO_FLAGS,
        payload={
            "reason": "open_review_flags",
            "openFlagCount": sum(1 for flag in recipe.review_flags if flag.status == RecipeReviewFlagStatus.OPEN),
        },
    )
    return embedding


def retry_recipe_embedding(session: Session, recipe_id: str, owner_id: str) -> RecipeEmbedding:
    recipe = get_owner_recipe_for_embedding_retry(session, recipe_id, owner_id)
    if recipe is None:
        raise ApiError(ApiErrorCode.RECIPE_NOT_FOUND, "Recipe not found.", status_code=404)
    _, provider = get_embedding_provider()
    embedding = get_or_create_recipe_embedding(session, recipe.id, model=provider.model)
    previous_status = embedding.status
    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=recipe.owner_id,
        event_type=EmbeddingEventType.RETRY_REQUESTED,
        payload={"source": "manual", "previousStatus": previous_status, "failedAttempts": embedding.failed_attempts},
    )
    embedding, should_enqueue = prepare_recipe_embedding(recipe, force=True)
    session.commit()
    if should_enqueue:
        enqueue_recipe_embedding_with_event(session, embedding=embedding, owner_id=recipe.owner_id)
        session.commit()
    session.refresh(embedding)
    return embedding


def process_recipe_embedding(session: Session, recipe_id: str) -> None:
    recipe = get_recipe_for_embedding(session, recipe_id)
    if recipe is None:
        return
    log = bind_logger(logger, component=EMBEDDING_LOG_COMPONENT, recipeId=recipe.id, ownerId=recipe.owner_id)
    if has_open_review_flags(session, recipe.id):
        skip_recipe_embedding_due_to_flags(session, recipe.id)
        session.commit()
        log.info(f"{EMBEDDING_LOG_PREFIX} Embedding skipped due to open review flags")
        return

    provider_name, provider = get_embedding_provider()
    input_text = build_recipe_embedding_input(recipe)
    input_hash = build_recipe_embedding_hash(recipe)
    embedding = get_or_create_recipe_embedding(session, recipe.id, model=provider.model)
    if embedding.status == RecipeEmbeddingStatus.READY.value and embedding.input_hash == input_hash and embedding.model == provider.model:
        add_embedding_event(
            session,
            embedding=embedding,
            owner_id=recipe.owner_id,
            event_type=EmbeddingEventType.ALREADY_READY,
            payload={"model": provider.model, "inputHash": input_hash},
        )
        session.commit()
        log.info(f"{EMBEDDING_LOG_PREFIX} Embedding already ready", provider=provider_name, model=provider.model)
        return

    embedding.status = RecipeEmbeddingStatus.RUNNING.value
    embedding.model = provider.model
    embedding.input_hash = input_hash
    embedding.last_attempt_at = _now()
    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=recipe.owner_id,
        event_type=EmbeddingEventType.STARTED,
        payload={"model": provider.model, "inputHash": input_hash},
    )
    session.commit()
    log.info(f"{EMBEDDING_LOG_PREFIX} Embedding started", provider=provider_name, model=provider.model)

    started_at = perf_counter()
    try:
        vector = provider.embed(input_text)
    except Exception as error:
        latest = get_recipe_embedding(session, recipe.id) or embedding
        latest.status = RecipeEmbeddingStatus.FAILED.value
        latest.error_message = repr(error)
        latest.failed_attempts += 1
        latest.last_error_at = _now()
        add_embedding_event(
            session,
            embedding=latest,
            owner_id=recipe.owner_id,
            event_type=EmbeddingEventType.FAILED,
            payload={
                "model": provider.model,
                "inputHash": input_hash,
                "error": repr(error),
                "temporary": True,
                "failedAttempts": latest.failed_attempts,
            },
        )
        session.commit()
        log.error(f"{EMBEDDING_LOG_PREFIX} Embedding provider threw", error=repr(error))
        raise
    duration_ms = int((perf_counter() - started_at) * 1000)
    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=recipe.owner_id,
        event_type=EmbeddingEventType.PROVIDER_SUCCEEDED,
        payload={"model": provider.model, "inputHash": input_hash, "dimension": len(vector), "durationMs": duration_ms},
    )

    session.expire_all()
    latest_recipe = get_recipe_for_embedding(session, recipe.id)
    if latest_recipe is None:
        return
    latest_hash = build_recipe_embedding_hash(latest_recipe)
    latest_embedding = get_or_create_recipe_embedding(session, latest_recipe.id, model=provider.model)
    if latest_hash != input_hash:
        latest_embedding.input_hash = latest_hash
        latest_embedding.status = RecipeEmbeddingStatus.STALE.value
        latest_embedding.error_message = None
        add_embedding_event(
            session,
            embedding=latest_embedding,
            owner_id=latest_recipe.owner_id,
            event_type=EmbeddingEventType.STALE_REQUEUED,
            payload={
                "reason": "recipe_changed_while_embedding",
                "taskInputHash": input_hash,
                "latestInputHash": latest_hash,
            },
        )
        session.commit()
        enqueue_recipe_embedding_with_event(session, embedding=latest_embedding, owner_id=latest_recipe.owner_id)
        session.commit()
        log.info(f"{EMBEDDING_LOG_PREFIX} Embedding input changed during provider call")
        return

    latest_embedding.embedding = vector
    latest_embedding.model = provider.model
    latest_embedding.input_hash = input_hash
    latest_embedding.status = RecipeEmbeddingStatus.READY.value
    latest_embedding.error_message = None
    add_embedding_event(
        session,
        embedding=latest_embedding,
        owner_id=latest_recipe.owner_id,
        event_type=EmbeddingEventType.SAVED,
        payload={"model": provider.model, "inputHash": input_hash, "dimension": len(vector)},
    )
    session.commit()
    log.info(f"{EMBEDDING_LOG_PREFIX} Embedding ready", provider=provider_name, model=provider.model)
