from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.query_utils import list_scalars_with_optional_pagination
from app.models import Collection, Recipe


def count_collections(session: Session, owner_id: str) -> int:
    return session.scalar(select(func.count()).select_from(Collection).where(Collection.owner_id == owner_id)) or 0


def list_collections(session: Session, owner_id: str, *, limit: int | None = None, offset: int | None = None) -> list[Collection]:
    query = select(Collection).where(Collection.owner_id == owner_id).options(selectinload(Collection.recipes)).order_by(Collection.name)
    return list_scalars_with_optional_pagination(session, query, limit=limit, offset=offset)


def get_collection(session: Session, collection_id: str, owner_id: str, *, include_recipes: bool = False) -> Collection | None:
    query = select(Collection).where(Collection.id == collection_id, Collection.owner_id == owner_id)
    if include_recipes:
        query = query.options(selectinload(Collection.recipes).selectinload(Recipe.cover_image))
    return session.scalar(query)


def get_collection_with_recipes(session: Session, collection_id: str, owner_id: str) -> Collection | None:
    return session.scalar(
        select(Collection).where(Collection.id == collection_id, Collection.owner_id == owner_id).options(selectinload(Collection.recipes))
    )
