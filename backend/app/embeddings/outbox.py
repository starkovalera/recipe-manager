import logging

from sqlalchemy.orm import Session

from app.core.logging import bind_logger
from app.embeddings.constants import EMBEDDING_LOG_COMPONENT
from app.embeddings.events import add_embedding_event
from app.embeddings.queries import get_recipe_embedding
from app.models import RecipeEmbeddingEventType

logger = logging.getLogger(__name__)


def record_embedding_enqueued(
    session: Session,
    recipe_id: str,
) -> None:
    embedding = get_recipe_embedding(session, recipe_id)
    if embedding is None:
        bind_logger(
            logger,
            component=EMBEDDING_LOG_COMPONENT,
            recipe_id=recipe_id,
        ).error("Published embedding task has no embedding row")
        return

    add_embedding_event(
        session,
        embedding=embedding,
        owner_id=embedding.recipe.owner_id,
        event_type=RecipeEmbeddingEventType.ENQUEUED,
        payload={
            "taskName": "embed_recipe",
            "recipeId": recipe_id,
        },
    )
