from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Collection, Recipe


def list_collections(session: Session, owner_id: str) -> list[Collection]:
    return session.scalars(
        select(Collection).where(Collection.owner_id == owner_id).options(selectinload(Collection.recipes)).order_by(Collection.name)
    ).all()


def get_collection(session: Session, collection_id: str, owner_id: str, *, include_recipes: bool = False) -> Collection | None:
    query = select(Collection).where(Collection.id == collection_id, Collection.owner_id == owner_id)
    if include_recipes:
        query = query.options(selectinload(Collection.recipes).selectinload(Recipe.images))
    return session.scalar(query)


def get_collection_with_recipes(session: Session, collection_id: str, owner_id: str) -> Collection | None:
    return session.scalar(
        select(Collection).where(Collection.id == collection_id, Collection.owner_id == owner_id).options(selectinload(Collection.recipes))
    )
