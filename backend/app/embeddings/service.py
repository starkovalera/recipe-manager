from sqlalchemy.orm import Session

from app.core.errors import RecipeNotFoundError
from app.embeddings.events import add_embedding_event
from app.embeddings.planning import prepare_recipe_embedding
from app.embeddings.queries import (
    get_or_create_recipe_embedding,
    get_recipe_for_embedding,
)
from app.embeddings.runtime import get_embedding_provider
from app.models import RecipeEmbedding, RecipeEmbeddingEventType
from app.queueing.outbox import dispatch_outbox_message


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
    if plan.outbox_message_id is not None:
        dispatch_outbox_message(plan.outbox_message_id)
    session.refresh(plan.embedding)
    return plan.embedding
