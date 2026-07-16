import dramatiq

from app.core.dramatiq import broker as _broker  # noqa: F401
from app.embeddings.processing import process_recipe_embedding


@dramatiq.actor(max_retries=3)
def embed_recipe_task(recipe_id: str) -> None:
    process_recipe_embedding(recipe_id)
