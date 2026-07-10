import logging
from datetime import datetime, timezone
from time import perf_counter

from sqlalchemy.orm import Session

from app.core.errors import RecipeNotFoundError
from app.core.logging import bind_logger
from app.embeddings.constants import EMBEDDING_LOG_COMPONENT, EMBEDDING_LOG_PREFIX
from app.embeddings.events import add_embedding_event
from app.embeddings.input import build_recipe_embedding_input
from app.embeddings.planning import prepare_recipe_embedding
from app.embeddings.queries import (
    get_or_create_recipe_embedding,
    get_recipe_embedding,
    get_recipe_for_embedding,
    has_open_review_flags,
)
from app.embeddings.runtime import get_embedding_provider
from app.models import RecipeEmbedding, RecipeEmbeddingEventType, RecipeEmbeddingStatus

logger = logging.getLogger(EMBEDDING_LOG_COMPONENT)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def enqueue_recipe_embedding(recipe_id: str) -> None:
    from app.embeddings.tasks import embed_recipe_task

    embed_recipe_task.send(recipe_id)


def enqueue_recipe_embedding_with_event(session: Session, *, embedding: RecipeEmbedding, owner_id: str) -> None:
    enqueue_recipe_embedding(embedding.recipe_id)
    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=owner_id,
        event_type=RecipeEmbeddingEventType.ENQUEUED,
        payload={"taskName": "embed_recipe", "recipeId": embedding.recipe_id},
    )


def retry_recipe_embedding(session: Session, recipe_id: str, owner_id: str) -> RecipeEmbedding:
    recipe = get_recipe_for_embedding(session, recipe_id, owner_id=owner_id)
    if recipe is None:
        raise RecipeNotFoundError()
    _, provider = get_embedding_provider()
    embedding = get_or_create_recipe_embedding(session, recipe.id, model=provider.model)
    previous_status = embedding.status
    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=recipe.owner_id,
        event_type=RecipeEmbeddingEventType.RETRY_REQUESTED,
        payload={"source": "manual", "previousStatus": previous_status, "failedAttempts": embedding.failed_attempts},
    )
    plan = prepare_recipe_embedding(session, recipe, force=True)
    session.commit()
    if plan.enqueue:
        enqueue_recipe_embedding_with_event(session, embedding=plan.embedding, owner_id=recipe.owner_id)
        session.commit()
    session.refresh(plan.embedding)
    return plan.embedding


def process_recipe_embedding(session: Session, recipe_id: str) -> None:
    recipe = get_recipe_for_embedding(session, recipe_id)
    if recipe is None:
        return
    log = bind_logger(logger, component=EMBEDDING_LOG_COMPONENT, recipeId=recipe.id, ownerId=recipe.owner_id)
    if has_open_review_flags(session, recipe.id):
        prepare_recipe_embedding(session, recipe)
        session.commit()
        log.info(f"{EMBEDDING_LOG_PREFIX} Embedding skipped due to open review flags")
        return

    provider_name, provider = get_embedding_provider()
    embedding_input = build_recipe_embedding_input(recipe)
    embedding = get_or_create_recipe_embedding(session, recipe.id, model=provider.model)
    if (
        embedding.status == RecipeEmbeddingStatus.READY
        and embedding.input_hash == embedding_input.input_hash
        and embedding.model == provider.model
    ):
        add_embedding_event(
            session,
            embedding=embedding,
            owner_id=recipe.owner_id,
            event_type=RecipeEmbeddingEventType.ALREADY_READY,
            payload={"model": provider.model, "inputHash": embedding_input.input_hash},
        )
        session.commit()
        log.info(f"{EMBEDDING_LOG_PREFIX} Embedding already ready", provider=provider_name, model=provider.model)
        return

    embedding.status = RecipeEmbeddingStatus.RUNNING
    embedding.model = provider.model
    embedding.input_hash = embedding_input.input_hash
    embedding.last_attempt_at = _now()
    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=recipe.owner_id,
        event_type=RecipeEmbeddingEventType.STARTED,
        payload={"model": provider.model, "inputHash": embedding_input.input_hash},
    )
    session.commit()
    log.info(f"{EMBEDDING_LOG_PREFIX} Embedding started", provider=provider_name, model=provider.model)

    started_at = perf_counter()
    try:
        vector = provider.embed(embedding_input.text)
    except Exception as error:
        latest = get_recipe_embedding(session, recipe.id) or embedding
        latest.status = RecipeEmbeddingStatus.FAILED
        latest.error_message = repr(error)
        latest.failed_attempts += 1
        latest.last_error_at = _now()
        add_embedding_event(
            session,
            embedding=latest,
            owner_id=recipe.owner_id,
            event_type=RecipeEmbeddingEventType.FAILED,
            payload={
                "model": provider.model,
                "inputHash": embedding_input.input_hash,
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
        event_type=RecipeEmbeddingEventType.PROVIDER_SUCCEEDED,
        payload={
            "model": provider.model,
            "inputHash": embedding_input.input_hash,
            "dimension": len(vector),
            "durationMs": duration_ms,
        },
    )

    session.expire_all()
    latest_recipe = get_recipe_for_embedding(session, recipe.id)
    if latest_recipe is None:
        return
    latest_input = build_recipe_embedding_input(latest_recipe)
    latest_embedding = get_or_create_recipe_embedding(session, latest_recipe.id, model=provider.model)
    if latest_input.input_hash != embedding_input.input_hash:
        latest_embedding.input_hash = latest_input.input_hash
        latest_embedding.status = RecipeEmbeddingStatus.STALE
        latest_embedding.error_message = None
        add_embedding_event(
            session,
            embedding=latest_embedding,
            owner_id=latest_recipe.owner_id,
            event_type=RecipeEmbeddingEventType.STALE_REQUEUED,
            payload={
                "reason": "recipe_changed_while_embedding",
                "taskInputHash": embedding_input.input_hash,
                "latestInputHash": latest_input.input_hash,
            },
        )
        session.commit()
        enqueue_recipe_embedding_with_event(session, embedding=latest_embedding, owner_id=latest_recipe.owner_id)
        session.commit()
        log.info(f"{EMBEDDING_LOG_PREFIX} Embedding input changed during provider call")
        return

    latest_embedding.embedding = vector
    latest_embedding.model = provider.model
    latest_embedding.input_hash = embedding_input.input_hash
    latest_embedding.status = RecipeEmbeddingStatus.READY
    latest_embedding.error_message = None
    add_embedding_event(
        session,
        embedding=latest_embedding,
        owner_id=latest_recipe.owner_id,
        event_type=RecipeEmbeddingEventType.SAVED,
        payload={"model": provider.model, "inputHash": embedding_input.input_hash, "dimension": len(vector)},
    )
    session.commit()
    log.info(f"{EMBEDDING_LOG_PREFIX} Embedding ready", provider=provider_name, model=provider.model)
