from sqlalchemy import exists, select
from sqlalchemy.orm import Session, selectinload

from app.models import Recipe, RecipeEmbedding, RecipeEmbeddingStatus, RecipeReviewFlag, RecipeReviewFlagStatus


def get_recipe_for_embedding(session: Session, recipe_id: str) -> Recipe | None:
    return session.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.review_flags),
            selectinload(Recipe.embedding),
        )
    )


def get_owner_recipe_for_embedding_retry(session: Session, recipe_id: str, owner_id: str) -> Recipe | None:
    return session.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id, Recipe.owner_id == owner_id)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.review_flags),
            selectinload(Recipe.embedding),
        )
    )


def get_recipe_embedding(session: Session, recipe_id: str) -> RecipeEmbedding | None:
    return session.get(RecipeEmbedding, recipe_id)


def get_recipe_embedding_with_recipe(session: Session, recipe_id: str) -> RecipeEmbedding | None:
    query = (
        select(RecipeEmbedding)
        .where(RecipeEmbedding.recipe_id == recipe_id)
        .options(selectinload(RecipeEmbedding.recipe))
    )
    return session.scalar(query)


def get_or_create_recipe_embedding(session: Session, recipe_id: str, *, model: str) -> RecipeEmbedding:
    embedding = get_recipe_embedding(session, recipe_id)
    if embedding is not None:
        return embedding

    embedding = RecipeEmbedding(
        recipe_id=recipe_id,
        model=model,
        status=RecipeEmbeddingStatus.STALE,
        embedding=None,
        input_hash=None,
    )
    session.add(embedding)
    session.flush()
    return embedding


def has_open_review_flags(session: Session, recipe_id: str) -> bool:
    return session.scalar(
        select(
            exists().where(
                RecipeReviewFlag.recipe_id == recipe_id,
                RecipeReviewFlag.status == RecipeReviewFlagStatus.OPEN,
            )
        )
    )
