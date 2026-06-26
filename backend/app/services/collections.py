from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError, ErrorCode
from app.models import Collection, Recipe
from app.schemas.collections import CollectionDetailOut, CollectionIn, CollectionListOut, CollectionOut
from app.schemas.recipes import RecipeListItemOut
from app.services.recipes import _serialize_image


def _recipe_list_item(recipe: Recipe) -> RecipeListItemOut:
    cover = next((image for image in recipe.images if image.id == recipe.cover_image_id), None)
    return RecipeListItemOut(
        id=recipe.id,
        title=recipe.title,
        coverImage=_serialize_image(cover) if cover else None,
        note=recipe.note,
        updatedAt=recipe.updated_at,
    )


def _collection_out(collection: Collection) -> CollectionOut:
    return CollectionOut(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        recipeCount=len(collection.recipes),
    )


def list_collections(session: Session, owner_id: str) -> CollectionListOut:
    collections = session.scalars(
        select(Collection).where(Collection.owner_id == owner_id).options(selectinload(Collection.recipes)).order_by(Collection.name)
    ).all()
    return CollectionListOut(items=[_collection_out(collection) for collection in collections])


def create_collection(session: Session, owner_id: str, payload: CollectionIn) -> CollectionDetailOut:
    collection = Collection(owner_id=owner_id, name=payload.name.strip(), description=payload.description.strip() if payload.description else None)
    session.add(collection)
    session.commit()
    return get_collection_detail(session, collection.id, owner_id)


def get_collection_detail(session: Session, collection_id: str, owner_id: str) -> CollectionDetailOut:
    collection = session.scalar(
        select(Collection)
        .where(Collection.id == collection_id, Collection.owner_id == owner_id)
        .options(selectinload(Collection.recipes).selectinload(Recipe.images))
    )
    if collection is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Collection not found.", status_code=404)
    base = _collection_out(collection)
    return CollectionDetailOut(**base.model_dump(), recipes=[_recipe_list_item(recipe) for recipe in collection.recipes])


def delete_collection(session: Session, collection_id: str, owner_id: str) -> None:
    collection = session.scalar(select(Collection).where(Collection.id == collection_id, Collection.owner_id == owner_id))
    if collection is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Collection not found.", status_code=404)
    session.delete(collection)
    session.commit()


def add_recipe_to_collection(session: Session, collection_id: str, recipe_id: str, owner_id: str) -> None:
    collection = session.scalar(
        select(Collection).where(Collection.id == collection_id, Collection.owner_id == owner_id).options(selectinload(Collection.recipes))
    )
    recipe = session.scalar(select(Recipe).where(Recipe.id == recipe_id, Recipe.owner_id == owner_id))
    if collection is None or recipe is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Collection or recipe not found.", status_code=404)
    if recipe not in collection.recipes:
        collection.recipes.append(recipe)
    session.commit()


def remove_recipe_from_collection(session: Session, collection_id: str, recipe_id: str, owner_id: str) -> None:
    collection = session.scalar(
        select(Collection).where(Collection.id == collection_id, Collection.owner_id == owner_id).options(selectinload(Collection.recipes))
    )
    if collection is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Collection not found.", status_code=404)
    collection.recipes = [recipe for recipe in collection.recipes if recipe.id != recipe_id]
    session.commit()
