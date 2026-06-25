from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.recipes import RecipeDetailOut, RecipeListOut, RecipePatchIn, ReviewFlagOut, ReviewFlagPatchIn
from app.services.recipes import get_recipe_detail, list_recipes, patch_recipe, set_review_flag_status

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=RecipeListOut)
def get_recipes(session: Session = Depends(get_session)) -> RecipeListOut:
    return list_recipes(session)


@router.get("/{recipe_id}", response_model=RecipeDetailOut)
def get_recipe(recipe_id: str, session: Session = Depends(get_session)) -> RecipeDetailOut:
    return get_recipe_detail(session, recipe_id)


@router.patch("/{recipe_id}", response_model=RecipeDetailOut)
def update_recipe(recipe_id: str, patch: RecipePatchIn, session: Session = Depends(get_session)) -> RecipeDetailOut:
    return patch_recipe(session, recipe_id, patch)


@router.patch("/{recipe_id}/review-flags/{flag_id}", response_model=ReviewFlagOut)
def update_review_flag(
    recipe_id: str,
    flag_id: str,
    patch: ReviewFlagPatchIn,
    session: Session = Depends(get_session),
) -> ReviewFlagOut:
    return set_review_flag_status(session, recipe_id, flag_id, patch.status)
