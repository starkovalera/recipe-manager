from app.db.session import db_session
from app.embeddings.events import add_embedding_event
from app.embeddings.logging import bind_embedding_logger
from app.embeddings.queries import get_recipe_embedding
from app.models import RecipeEmbeddingEventType
from app.queueing.provider import get_queue_publisher


def enqueue_recipe_embedding(recipe_id: str, owner_id: str) -> bool:
    log = bind_embedding_logger(
        recipe_id=recipe_id,
        owner_id=owner_id,
    )
    try:
        get_queue_publisher().publish_recipe_embedding(recipe_id)
    except Exception as error:
        log.error("Embedding task publish failed", error=repr(error))
        return False

    try:
        with db_session() as session:
            embedding = get_recipe_embedding(session, recipe_id)
            if embedding is None:
                log.error("Published embedding task has no embedding row")
                return True
            add_embedding_event(
                session,
                embedding=embedding,
                owner_id=owner_id,
                event_type=RecipeEmbeddingEventType.ENQUEUED,
                payload={"taskName": "embed_recipe", "recipeId": recipe_id},
            )
    except Exception as error:
        log.error("Embedding enqueued event persistence failed", error=repr(error))
    return True
