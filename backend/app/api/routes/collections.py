from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentUserDep, SessionDep
from app.core.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
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
def get_collections(
    session: SessionDep,
    current_user: CurrentUserDep,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, list[Collection] | int]:
    collections, total = list_collections(session, current_user.id, limit=limit, offset=offset)
    return {"items": collections, "total": total, "limit": limit, "offset": offset}


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
