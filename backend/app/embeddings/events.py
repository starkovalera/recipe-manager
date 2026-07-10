from typing import Any

from sqlalchemy.orm import Session

from app.models import RecipeEmbedding, RecipeEmbeddingEvent, RecipeEmbeddingEventType


def add_embedding_event(
    session: Session,
    *,
    embedding: RecipeEmbedding,
    owner_id: str,
    event_type: RecipeEmbeddingEventType,
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
