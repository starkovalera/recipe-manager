from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.query_utils import list_scalars_with_optional_pagination
from app.models import Ingredient, Recipe, RecipeImage, RecipeResource, RecipeReviewFlag, Tag
from app.recipes.filters import RecipeListFilters
from app.services.search_text import normalize_search_text


def get_recipe(session: Session, recipe_id: str, owner_id: str) -> Recipe | None:
    return session.scalar(select(Recipe).where(Recipe.id == recipe_id, Recipe.owner_id == owner_id))


def apply_recipe_list_filters(query: Select[Any], filters: RecipeListFilters) -> Select[Any]:
    if filters.tag_id is not None:
        query = query.where(Recipe.tags.any(Tag.id == filters.tag_id))
    for ingredient_query in filters.ingredient_queries:
        normalized_query = normalize_search_text(ingredient_query)
        if normalized_query:
            query = query.where(Recipe.ingredients.any(Ingredient.search_name.contains(normalized_query)))
    if filters.source_name is not None:
        query = query.where(Recipe.source_name == filters.source_name)
    if filters.author_name is not None:
        query = query.where(Recipe.author_name == filters.author_name)
    if filters.title_recipe_id is not None:
        query = query.where(Recipe.id == filters.title_recipe_id)
    return query


def count_recipes(session: Session, owner_id: str, *, filters: RecipeListFilters | None = None) -> int:
    query = select(func.count()).select_from(Recipe).where(Recipe.owner_id == owner_id)
    if filters is not None:
        query = apply_recipe_list_filters(query, filters)
    return session.scalar(query) or 0


def list_recipes(
    session: Session,
    owner_id: str,
    *,
    filters: RecipeListFilters | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[Recipe]:
    query = (
        select(Recipe)
        .where(Recipe.owner_id == owner_id)
        .options(selectinload(Recipe.cover_image), selectinload(Recipe.review_flags))
        .order_by(Recipe.created_at.desc())
    )
    if filters is not None:
        query = apply_recipe_list_filters(query, filters)
    return list_scalars_with_optional_pagination(session, query, limit=limit, offset=offset)


def get_recipe_detail(session: Session, recipe_id: str, owner_id: str) -> Recipe | None:
    return session.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id, Recipe.owner_id == owner_id)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.cover_image),
            selectinload(Recipe.resources).selectinload(RecipeResource.image),
            selectinload(Recipe.review_flags),
            selectinload(Recipe.tags),
            selectinload(Recipe.collections),
        )
    )


def get_recipe_for_embedding_input_preview(session: Session, recipe_id: str) -> Recipe | None:
    return session.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(selectinload(Recipe.ingredients))
    )


def get_recipe_for_resource_mutation(session: Session, recipe_id: str, owner_id: str) -> Recipe | None:
    return session.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id, Recipe.owner_id == owner_id)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.cover_image),
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
