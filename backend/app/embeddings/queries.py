from sqlalchemy import exists, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql import Select

from app.models import Recipe, RecipeEmbedding, RecipeEmbeddingStatus, RecipeReviewFlag, RecipeReviewFlagStatus, RecipeStatus


def build_active_recipe_for_embedding_for_update_statement(recipe_id: str) -> Select:
    return (
        select(Recipe)
        .where(
            Recipe.id == recipe_id,
            Recipe.status == RecipeStatus.ACTIVE,
        )
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.review_flags),
            selectinload(Recipe.embedding),
        )
        .with_for_update()
    )


def get_active_recipe_for_embedding_for_update(
    session: Session,
    recipe_id: str,
) -> Recipe | None:
    return session.scalar(build_active_recipe_for_embedding_for_update_statement(recipe_id))


def get_recipe_for_embedding(
    session: Session,
    recipe_id: str,
    *,
    owner_id: str | None = None,
    status: RecipeStatus | None = RecipeStatus.ACTIVE,
) -> Recipe | None:
    query = select(Recipe).where(Recipe.id == recipe_id)
    if owner_id is not None:
        query = query.where(Recipe.owner_id == owner_id)
    if status is not None:
        query = query.where(Recipe.status == status)
    return session.scalar(
        query.options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.review_flags),
            selectinload(Recipe.embedding),
        )
    )


def list_internal_recipe_embeddings(
    session: Session,
    *,
    owner_id: str | None = None,
    status: RecipeStatus | None = RecipeStatus.ACTIVE,
) -> list[RecipeEmbedding]:
    statement = (
        select(RecipeEmbedding)
        .join(Recipe)
        .options(selectinload(RecipeEmbedding.recipe), selectinload(RecipeEmbedding.events))
        .order_by(RecipeEmbedding.updated_at.desc(), RecipeEmbedding.created_at.desc())
    )
    if owner_id is not None:
        statement = statement.where(Recipe.owner_id == owner_id)
    if status is not None:
        statement = statement.where(Recipe.status == status)
    return list(session.scalars(statement))


def get_recipe_embedding(session: Session, recipe_id: str) -> RecipeEmbedding | None:
    return session.get(RecipeEmbedding, recipe_id)


def get_recipe_embedding_with_recipe(
    session: Session,
    recipe_id: str,
    *,
    status: RecipeStatus | None = RecipeStatus.ACTIVE,
) -> RecipeEmbedding | None:
    query = (
        select(RecipeEmbedding)
        .join(Recipe, Recipe.id == RecipeEmbedding.recipe_id)
        .where(RecipeEmbedding.recipe_id == recipe_id)
        .options(selectinload(RecipeEmbedding.recipe))
    )
    if status is not None:
        query = query.where(Recipe.status == status)
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
