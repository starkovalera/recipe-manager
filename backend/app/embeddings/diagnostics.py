from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import RecipeEmbedding


def list_internal_recipe_embeddings(session: Session) -> list[RecipeEmbedding]:
    return list(
        session.scalars(
            select(RecipeEmbedding)
            .options(selectinload(RecipeEmbedding.recipe))
            .order_by(RecipeEmbedding.updated_at.desc(), RecipeEmbedding.created_at.desc())
        )
    )
