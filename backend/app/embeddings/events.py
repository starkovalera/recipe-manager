from typing import Any

from sqlalchemy.orm import Session

from app.models import RecipeEmbedding, RecipeEmbeddingEvent


class EmbeddingEventType:
    SCHEDULED = "scheduled"
    ENQUEUED = "enqueued"
    STARTED = "started"
    SKIPPED_DUE_TO_FLAGS = "skipped_due_to_flags"
    ALREADY_READY = "already_ready"
    PROVIDER_SUCCEEDED = "provider_succeeded"
    SAVED = "saved"
    STALE_REQUEUED = "stale_requeued"
    FAILED = "failed"
    RETRY_REQUESTED = "retry_requested"


def add_embedding_event(
    session: Session,
    *,
    embedding: RecipeEmbedding,
    owner_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> RecipeEmbeddingEvent:
    event = RecipeEmbeddingEvent(
        recipe_id=embedding.recipe_id,
        owner_id=owner_id,
        event_type=event_type,
        status_after=embedding.status,
        payload=payload,
    )
    session.add(event)
    return event
