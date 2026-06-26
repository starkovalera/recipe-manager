from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models import User
from app.schemas.recipes import RecipeDetailOut, RecipeListOut, RecipePatchIn, RecipeSourcePatchIn, ReviewFlagOut, ReviewFlagPatchIn
from app.services.recipes import delete_recipe, get_recipe_detail, list_recipes, patch_recipe, patch_recipe_source_status, set_review_flag_status

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=RecipeListOut)
def get_recipes(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)) -> RecipeListOut:
    return list_recipes(session, current_user.id)


@router.get("/{recipe_id}", response_model=RecipeDetailOut)
def get_recipe(recipe_id: str, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)) -> RecipeDetailOut:
    return get_recipe_detail(session, recipe_id, current_user.id)


@router.patch("/{recipe_id}", response_model=RecipeDetailOut)
def update_recipe(
    recipe_id: str,
    patch: RecipePatchIn,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> RecipeDetailOut:
    return patch_recipe(session, recipe_id, current_user.id, patch)


@router.delete("/{recipe_id}", status_code=204)
def remove_recipe(recipe_id: str, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)) -> Response:
    delete_recipe(session, recipe_id, current_user.id)
    return Response(status_code=204)


@router.patch("/{recipe_id}/review-flags/{flag_id}", response_model=ReviewFlagOut)
def update_review_flag(
    recipe_id: str,
    flag_id: str,
    patch: ReviewFlagPatchIn,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReviewFlagOut:
    return set_review_flag_status(session, recipe_id, current_user.id, flag_id, patch.status)


@router.patch("/{recipe_id}/sources/{source_id}", response_model=RecipeDetailOut)
def update_recipe_source(
    recipe_id: str,
    source_id: str,
    patch: RecipeSourcePatchIn,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> RecipeDetailOut:
    return patch_recipe_source_status(session, recipe_id, current_user.id, source_id, patch.status)
