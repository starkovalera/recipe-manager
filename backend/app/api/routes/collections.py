from fastapi import APIRouter, Response

from app.api.deps import CurrentUserDep, SessionDep
from app.models import Collection
from app.schemas.collections import CollectionDetailOut, CollectionIn, CollectionListOut
from app.services.collections import (
    add_recipe_to_collection,
    create_collection,
    delete_collection,
    get_collection_detail,
    list_collections,
    remove_recipe_from_collection,
)

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("", response_model=CollectionListOut)
def get_collections(session: SessionDep, current_user: CurrentUserDep) -> dict[str, list[Collection]]:
    return {"items": list_collections(session, current_user.id)}


@router.post("", response_model=CollectionDetailOut)
def post_collection(
    payload: CollectionIn,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Collection:
    return create_collection(session, current_user.id, payload)


@router.get("/{collection_id}", response_model=CollectionDetailOut)
def get_collection(
    collection_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Collection:
    return get_collection_detail(session, collection_id, current_user.id)


@router.delete("/{collection_id}", status_code=204)
def remove_collection(collection_id: str, session: SessionDep, current_user: CurrentUserDep) -> Response:
    delete_collection(session, collection_id, current_user.id)
    return Response(status_code=204)


@router.put("/{collection_id}/recipes/{recipe_id}", status_code=204)
def add_collection_recipe(
    collection_id: str,
    recipe_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    add_recipe_to_collection(session, collection_id, recipe_id, current_user.id)
    return Response(status_code=204)


@router.delete("/{collection_id}/recipes/{recipe_id}", status_code=204)
def remove_collection_recipe(
    collection_id: str,
    recipe_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    remove_recipe_from_collection(session, collection_id, recipe_id, current_user.id)
    return Response(status_code=204)
