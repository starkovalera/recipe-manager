from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.access.constants import UserRole
from app.access.rules import has_role
from app.api.deps import CurrentUserDep, SessionDep
from app.core.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from app.embeddings.service import retry_recipe_embedding
from app.models import Recipe, RecipeEmbedding, RecipeReviewFlag, SourceName
from app.recipes.filters import RecipeListFilters
from app.recipes.presentation import build_recipe_detail_response
from app.schemas.recipes import (
    RecipeDetailOut,
    RecipeEmbeddingOut,
    RecipeListOut,
    RecipePatchIn,
    RecipeResourcePatchIn,
    ReviewFlagOut,
    ReviewFlagPatchIn,
)
from app.services.recipes import (
    delete_recipe,
    get_recipe_detail,
    list_recipes,
    patch_recipe,
    patch_recipe_resource_status,
    set_review_flag_status,
)

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=RecipeListOut)
def get_recipes(
    session: SessionDep,
    current_user: CurrentUserDep,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
    tag: str | None = None,
    ingredient_query: Annotated[list[str] | None, Query(alias="ingredientQuery")] = None,
    source_name: Annotated[SourceName | None, Query(alias="sourceName")] = None,
    author_name: Annotated[str | None, Query(alias="authorName")] = None,
    title: str | None = None,
) -> dict[str, list[Recipe] | int]:
    filters = RecipeListFilters(
        tag_id=tag,
        ingredient_queries=tuple(ingredient_query or ()),
        source_name=source_name,
        author_name=author_name,
        title_recipe_id=title,
    )
    recipes, total = list_recipes(session, current_user.id, filters=filters, limit=limit, offset=offset)
    return {"items": recipes, "total": total, "limit": limit, "offset": offset}


@router.get("/{recipe_id}", response_model=RecipeDetailOut)
def get_recipe(recipe_id: str, session: SessionDep, current_user: CurrentUserDep) -> RecipeDetailOut:
    recipe = get_recipe_detail(session, recipe_id, current_user.id)
    return build_recipe_detail_response(recipe, include_debug=has_role(current_user, UserRole.DEBUG))


@router.patch("/{recipe_id}", response_model=RecipeDetailOut)
def update_recipe(
    recipe_id: str,
    patch: RecipePatchIn,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> RecipeDetailOut:
    recipe = patch_recipe(session, recipe_id, current_user.id, patch)
    return build_recipe_detail_response(recipe, include_debug=has_role(current_user, UserRole.DEBUG))


@router.delete("/{recipe_id}", status_code=204)
def remove_recipe(recipe_id: str, session: SessionDep, current_user: CurrentUserDep) -> Response:
    delete_recipe(session, recipe_id, current_user.id)
    return Response(status_code=204)


@router.patch("/{recipe_id}/review-flags/{flag_id}", response_model=ReviewFlagOut)
def update_review_flag(
    recipe_id: str,
    flag_id: str,
    patch: ReviewFlagPatchIn,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> RecipeReviewFlag:
    return set_review_flag_status(session, recipe_id, current_user.id, flag_id, patch.status)


@router.post("/{recipe_id}/embedding/retry", response_model=RecipeEmbeddingOut)
def retry_embedding(recipe_id: str, session: SessionDep, current_user: CurrentUserDep) -> RecipeEmbedding:
    return retry_recipe_embedding(session, recipe_id, current_user.id)


@router.patch("/{recipe_id}/resources/{resource_id}", response_model=RecipeDetailOut)
@router.patch("/{recipe_id}/sources/{resource_id}", response_model=RecipeDetailOut)
def update_recipe_resource(
    recipe_id: str,
    resource_id: str,
    patch: RecipeResourcePatchIn,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> RecipeDetailOut:
    recipe = patch_recipe_resource_status(session, recipe_id, current_user.id, resource_id, patch.status)
    return build_recipe_detail_response(recipe, include_debug=has_role(current_user, UserRole.DEBUG))
