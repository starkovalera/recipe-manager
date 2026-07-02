from sqlalchemy.orm import Session

from app.collections.queries import count_collections, get_collection, get_collection_with_recipes, list_collections as query_collections
from app.core.errors import ApiError, ErrorCode
from app.models import Collection
from app.recipes.queries import get_recipe
from app.schemas.collections import CollectionIn


def list_collections(session: Session, owner_id: str, *, limit: int, offset: int) -> tuple[list[Collection], int]:
    return query_collections(session, owner_id, limit=limit, offset=offset), count_collections(session, owner_id)


def create_collection(session: Session, owner_id: str, payload: CollectionIn) -> Collection:
    collection = Collection(owner_id=owner_id, name=payload.name.strip(), description=payload.description.strip() if payload.description else None)
    session.add(collection)
    session.commit()
    return get_collection_detail(session, collection.id, owner_id)


def get_collection_detail(session: Session, collection_id: str, owner_id: str) -> Collection:
    collection = get_collection(session, collection_id, owner_id, include_recipes=True)
    if collection is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Collection not found.", status_code=404)
    return collection


def delete_collection(session: Session, collection_id: str, owner_id: str) -> None:
    collection = get_collection(session, collection_id, owner_id)
    if collection is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Collection not found.", status_code=404)
    session.delete(collection)
    session.commit()


def add_recipe_to_collection(session: Session, collection_id: str, recipe_id: str, owner_id: str) -> None:
    collection = get_collection_with_recipes(session, collection_id, owner_id)
    recipe = get_recipe(session, recipe_id, owner_id)
    if collection is None or recipe is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Collection or recipe not found.", status_code=404)
    if recipe not in collection.recipes:
        collection.recipes.append(recipe)
    session.commit()


def remove_recipe_from_collection(session: Session, collection_id: str, recipe_id: str, owner_id: str) -> None:
    collection = get_collection_with_recipes(session, collection_id, owner_id)
    if collection is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Collection not found.", status_code=404)
    collection.recipes = [recipe for recipe in collection.recipes if recipe.id != recipe_id]
    session.commit()
