from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload, with_loader_criteria

from app.db.query_utils import list_scalars_with_optional_pagination
from app.models import Collection, Recipe, RecipeStatus


def _apply_recipe_loader_status(query: Select[Any], status: RecipeStatus | None) -> Select[Any]:
    if status is not None:
        query = query.options(with_loader_criteria(Recipe, Recipe.status == status, include_aliases=True))
    return query


def count_collections(session: Session, owner_id: str) -> int:
    return session.scalar(select(func.count()).select_from(Collection).where(Collection.owner_id == owner_id)) or 0


def list_collections(
    session: Session,
    owner_id: str,
    *,
    limit: int | None = None,
    offset: int | None = None,
    recipe_status: RecipeStatus | None = RecipeStatus.ACTIVE,
) -> list[Collection]:
    query = select(Collection).where(Collection.owner_id == owner_id).options(selectinload(Collection.recipes)).order_by(Collection.name)
    query = _apply_recipe_loader_status(query, recipe_status)
    return list_scalars_with_optional_pagination(session, query, limit=limit, offset=offset)


def get_collection(
    session: Session,
    collection_id: str,
    owner_id: str,
    *,
    include_recipes: bool = False,
    recipe_status: RecipeStatus | None = RecipeStatus.ACTIVE,
) -> Collection | None:
    query = select(Collection).where(Collection.id == collection_id, Collection.owner_id == owner_id)
    if include_recipes:
        query = query.options(selectinload(Collection.recipes).selectinload(Recipe.cover_image))
        query = _apply_recipe_loader_status(query, recipe_status)
    return session.scalar(query)


def get_collection_with_recipes(
    session: Session,
    collection_id: str,
    owner_id: str,
    *,
    recipe_status: RecipeStatus | None = RecipeStatus.ACTIVE,
) -> Collection | None:
    query = (
        select(Collection).where(Collection.id == collection_id, Collection.owner_id == owner_id).options(selectinload(Collection.recipes))
    )
    return session.scalar(_apply_recipe_loader_status(query, recipe_status))
