import dramatiq

from app.core.dramatiq import broker as _broker  # noqa: F401
from app.db.session import SessionLocal
from app.embeddings.service import process_recipe_embedding


def run_embedding_job(recipe_id: str) -> None:
    with SessionLocal() as session:
        process_recipe_embedding(session, recipe_id)


@dramatiq.actor(max_retries=3)
def embed_recipe_task(recipe_id: str) -> None:
    run_embedding_job(recipe_id)
