from fastapi import APIRouter, Response

from app.api.deps import CurrentUserDep, SessionDep
from app.models import Recipe, RecipeReviewFlag
from app.schemas.recipes import RecipeDetailOut, RecipeListOut, RecipePatchIn, RecipeResourcePatchIn, ReviewFlagOut, ReviewFlagPatchIn
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
def get_recipes(session: SessionDep, current_user: CurrentUserDep) -> dict[str, list[Recipe]]:
    return {"items": list_recipes(session, current_user.id)}


@router.get("/{recipe_id}", response_model=RecipeDetailOut)
def get_recipe(recipe_id: str, session: SessionDep, current_user: CurrentUserDep) -> Recipe:
    return get_recipe_detail(session, recipe_id, current_user.id)


@router.patch("/{recipe_id}", response_model=RecipeDetailOut)
def update_recipe(
    recipe_id: str,
    patch: RecipePatchIn,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Recipe:
    return patch_recipe(session, recipe_id, current_user.id, patch)


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


@router.patch("/{recipe_id}/resources/{resource_id}", response_model=RecipeDetailOut)
@router.patch("/{recipe_id}/sources/{resource_id}", response_model=RecipeDetailOut)
def update_recipe_resource(
    recipe_id: str,
    resource_id: str,
    patch: RecipeResourcePatchIn,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Recipe:
    return patch_recipe_resource_status(session, recipe_id, current_user.id, resource_id, patch.status)
