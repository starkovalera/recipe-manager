from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter

from sqlalchemy.orm import Session

from app.db.session import db_session
from app.embeddings.events import add_embedding_event
from app.embeddings.input import RecipeEmbeddingInput, build_recipe_embedding_input
from app.embeddings.logging import bind_embedding_logger
from app.embeddings.planning import prepare_recipe_embedding
from app.embeddings.queries import (
    get_or_create_recipe_embedding,
    get_recipe_embedding,
    get_recipe_for_embedding,
    has_open_review_flags,
)
from app.embeddings.runtime import get_embedding_provider
from app.models import RecipeEmbeddingEventType, RecipeEmbeddingStatus
from app.queueing.constants import QueueMessageType
from app.queueing.outbox import dispatch_outbox_message, schedule_outbox_message


@dataclass(frozen=True)
class EmbeddingProcessingContext:
    recipe_id: str
    owner_id: str
    provider_name: str
    model: str
    embedding_input: RecipeEmbeddingInput


def start_recipe_embedding(
    session: Session,
    recipe_id: str,
    *,
    provider_name: str,
    model: str,
) -> EmbeddingProcessingContext | None:
    recipe = get_recipe_for_embedding(session, recipe_id)
    if recipe is None:
        return None

    if has_open_review_flags(session, recipe.id):
        prepare_recipe_embedding(session, recipe)
        return None

    embedding_input = build_recipe_embedding_input(recipe)
    embedding = get_or_create_recipe_embedding(session, recipe.id, model=model)
    if embedding.status == RecipeEmbeddingStatus.READY and embedding.input_hash == embedding_input.input_hash and embedding.model == model:
        add_embedding_event(
            session,
            embedding=embedding,
            owner_id=recipe.owner_id,
            event_type=RecipeEmbeddingEventType.ALREADY_READY,
            payload={"model": model, "inputHash": embedding_input.input_hash},
        )
        return None

    embedding.status = RecipeEmbeddingStatus.RUNNING
    embedding.model = model
    embedding.input_hash = embedding_input.input_hash
    embedding.last_attempt_at = datetime.now(timezone.utc)
    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=recipe.owner_id,
        event_type=RecipeEmbeddingEventType.STARTED,
        payload={"model": model, "inputHash": embedding_input.input_hash},
    )
    return EmbeddingProcessingContext(
        recipe_id=recipe.id,
        owner_id=recipe.owner_id,
        provider_name=provider_name,
        model=model,
        embedding_input=embedding_input,
    )


def complete_recipe_embedding(
    session: Session,
    context: EmbeddingProcessingContext,
    vector: list[float],
    *,
    duration_ms: int,
) -> str | None:
    recipe = get_recipe_for_embedding(session, context.recipe_id)
    if recipe is None:
        return None

    embedding = get_recipe_embedding(session, recipe.id)
    if embedding is None:
        return None

    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=context.owner_id,
        event_type=RecipeEmbeddingEventType.PROVIDER_SUCCEEDED,
        payload={
            "model": context.model,
            "inputHash": context.embedding_input.input_hash,
            "dimension": len(vector),
            "durationMs": duration_ms,
        },
    )

    current_input = build_recipe_embedding_input(recipe)
    if current_input.input_hash != context.embedding_input.input_hash:
        embedding.input_hash = current_input.input_hash
        embedding.status = RecipeEmbeddingStatus.STALE
        embedding.error_message = None
        add_embedding_event(
            session,
            embedding=embedding,
            owner_id=context.owner_id,
            event_type=RecipeEmbeddingEventType.STALE_REQUEUED,
            payload={
                "reason": "recipe_changed_while_embedding",
                "taskInputHash": context.embedding_input.input_hash,
                "latestInputHash": current_input.input_hash,
            },
        )
        return schedule_outbox_message(
            session,
            QueueMessageType.RECIPE_EMBEDDING,
            recipe.id,
        ).id

    embedding.embedding = vector
    embedding.model = context.model
    embedding.input_hash = context.embedding_input.input_hash
    embedding.status = RecipeEmbeddingStatus.READY
    embedding.error_message = None
    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=context.owner_id,
        event_type=RecipeEmbeddingEventType.SAVED,
        payload={
            "model": context.model,
            "inputHash": context.embedding_input.input_hash,
            "dimension": len(vector),
        },
    )
    return None


def fail_recipe_embedding(
    session: Session,
    context: EmbeddingProcessingContext,
    error: Exception,
) -> int | None:
    embedding = get_recipe_embedding(session, context.recipe_id)
    if embedding is None:
        return None

    embedding.status = RecipeEmbeddingStatus.FAILED
    embedding.error_message = repr(error)
    embedding.failed_attempts += 1
    embedding.last_error_at = datetime.now(timezone.utc)
    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=context.owner_id,
        event_type=RecipeEmbeddingEventType.FAILED,
        payload={
            "model": context.model,
            "inputHash": context.embedding_input.input_hash,
            "error": repr(error),
            "temporary": True,
            "failedAttempts": embedding.failed_attempts,
        },
    )
    return embedding.failed_attempts


def process_recipe_embedding(recipe_id: str) -> None:
    provider_name, provider = get_embedding_provider()
    with db_session() as session:
        context = start_recipe_embedding(
            session,
            recipe_id,
            provider_name=provider_name,
            model=provider.model,
        )
    if context is None:
        return

    log = bind_embedding_logger(
        recipe_id=context.recipe_id,
        owner_id=context.owner_id,
        provider_name=provider_name,
        model=provider.model,
        input_hash=context.embedding_input.input_hash,
    )
    log.info("Embedding processing started")

    started_at = perf_counter()
    try:
        vector = provider.embed(context.embedding_input.text)
    except Exception as error:
        with db_session() as session:
            failed_attempts = fail_recipe_embedding(session, context, error)
        log.error(
            "Embedding provider failed",
            error=repr(error),
            failed_attempts=failed_attempts,
            duration_ms=int((perf_counter() - started_at) * 1000),
        )
        raise
    duration_ms = int((perf_counter() - started_at) * 1000)

    with db_session() as session:
        outbox_message_id = complete_recipe_embedding(
            session,
            context,
            vector,
            duration_ms=duration_ms,
        )

    if outbox_message_id is not None:
        dispatch_outbox_message(outbox_message_id)
        log.info("Embedding input changed during provider call", duration_ms=duration_ms)
        return

    log.info("Embedding saved", duration_ms=duration_ms)
