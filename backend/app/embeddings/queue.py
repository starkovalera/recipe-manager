import logging

from app.core.logging import bind_logger
from app.db.session import db_session
from app.embeddings.constants import EMBEDDING_LOG_COMPONENT, EMBEDDING_LOG_PREFIX
from app.embeddings.events import add_embedding_event
from app.embeddings.queries import get_recipe_embedding
from app.models import RecipeEmbeddingEventType

logger = logging.getLogger(EMBEDDING_LOG_COMPONENT)


def enqueue_recipe_embedding(recipe_id: str, owner_id: str) -> bool:
    from app.embeddings.tasks import embed_recipe_task

    log = bind_logger(
        logger,
        component=EMBEDDING_LOG_COMPONENT,
        recipe_id=recipe_id,
        owner_id=owner_id,
    )
    try:
        embed_recipe_task.send(recipe_id)
    except Exception as error:
        log.error(f"{EMBEDDING_LOG_PREFIX} Embedding task publish failed", error=repr(error))
        return False

    try:
        with db_session() as session:
            embedding = get_recipe_embedding(session, recipe_id)
            if embedding is None:
                log.error(f"{EMBEDDING_LOG_PREFIX} Published embedding task has no embedding row")
                return True
            add_embedding_event(
                session,
                embedding=embedding,
                owner_id=owner_id,
                event_type=RecipeEmbeddingEventType.ENQUEUED,
                payload={"taskName": "embed_recipe", "recipeId": recipe_id},
            )
    except Exception as error:
        log.error(f"{EMBEDDING_LOG_PREFIX} Embedding enqueued event persistence failed", error=repr(error))
    return True
