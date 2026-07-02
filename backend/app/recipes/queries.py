from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.query_utils import list_scalars_with_optional_pagination
from app.models import Recipe, RecipeImage, RecipeResource, RecipeReviewFlag


def get_recipe(session: Session, recipe_id: str, owner_id: str) -> Recipe | None:
    return session.scalar(select(Recipe).where(Recipe.id == recipe_id, Recipe.owner_id == owner_id))


def count_recipes(session: Session, owner_id: str) -> int:
    return session.scalar(select(func.count()).select_from(Recipe).where(Recipe.owner_id == owner_id)) or 0


def list_recipes(session: Session, owner_id: str, *, limit: int | None = None, offset: int | None = None) -> list[Recipe]:
    query = (
        select(Recipe)
        .where(Recipe.owner_id == owner_id)
        .options(selectinload(Recipe.images), selectinload(Recipe.review_flags))
        .order_by(Recipe.created_at.desc())
    )
    return list_scalars_with_optional_pagination(session, query, limit=limit, offset=offset)


def get_recipe_detail(session: Session, recipe_id: str, owner_id: str) -> Recipe | None:
    return session.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id, Recipe.owner_id == owner_id)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.images),
            selectinload(Recipe.resources).selectinload(RecipeResource.image),
            selectinload(Recipe.review_flags),
            selectinload(Recipe.tags),
            selectinload(Recipe.collections),
        )
    )


def get_recipe_for_resource_mutation(session: Session, recipe_id: str, owner_id: str) -> Recipe | None:
    return session.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id, Recipe.owner_id == owner_id)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.images),
            selectinload(Recipe.resources).selectinload(RecipeResource.children),
            selectinload(Recipe.review_flags),
            selectinload(Recipe.tags),
            selectinload(Recipe.collections),
        )
    )


def get_recipe_image(session: Session, image_id: str, recipe_id: str) -> RecipeImage | None:
    return session.scalar(select(RecipeImage).where(RecipeImage.id == image_id, RecipeImage.recipe_id == recipe_id))


def get_recipe_review_flag(session: Session, flag_id: str, recipe_id: str, owner_id: str) -> RecipeReviewFlag | None:
    return session.scalar(
        select(RecipeReviewFlag).where(
            RecipeReviewFlag.id == flag_id,
            RecipeReviewFlag.recipe_id == recipe_id,
            RecipeReviewFlag.owner_id == owner_id,
        )
    )
