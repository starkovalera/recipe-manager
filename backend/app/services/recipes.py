from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.models import Recipe, RecipeReviewFlag, RecipeReviewFlagStatus
from app.schemas.recipes import (
    IngredientOut,
    RecipeDetailOut,
    RecipeImageOut,
    RecipeListItemOut,
    RecipeListOut,
    RecipePatchIn,
    RecipeSourceOut,
    ReviewFlagOut,
)


def _image_url(storage_key: str) -> str:
    return f"/media/{storage_key}"


def _serialize_image(image) -> RecipeImageOut:
    return RecipeImageOut(
        id=image.id,
        role=image.role.value,
        mediaUrl=_image_url(image.storage_key),
        sourceImageId=image.source_image_id,
    )


def _serialize_flag(flag: RecipeReviewFlag) -> ReviewFlagOut:
    return ReviewFlagOut(
        id=flag.id,
        type=flag.type.value,
        status=flag.status.value,
        reasonCode=flag.reason_code,
        message=flag.message,
        details=flag.details,
        resolvedAt=flag.resolved_at,
    )


def _serialize_recipe_detail(recipe: Recipe) -> RecipeDetailOut:
    source_images = sorted([image for image in recipe.images if image.role.value == "SOURCE"], key=lambda item: item.position)
    cover_image = next((image for image in recipe.images if image.id == recipe.cover_image_id), None)
    return RecipeDetailOut(
        id=recipe.id,
        title=recipe.title,
        note=recipe.note,
        updatedAt=recipe.updated_at,
        servings=recipe.servings,
        cookTimeMinutes=recipe.cook_time_minutes,
        instructions=recipe.instructions,
        ingredients=[
            IngredientOut(
                id=ingredient.id,
                name=ingredient.name,
                quantity=ingredient.quantity,
                unit=ingredient.unit,
                note=ingredient.note,
                position=ingredient.position,
            )
            for ingredient in sorted(recipe.ingredients, key=lambda item: item.position)
        ],
        images=[_serialize_image(image) for image in source_images],
        coverImage=_serialize_image(cover_image) if cover_image else None,
        sources=[
            RecipeSourceOut(
                id=source.id,
                type=source.type.value,
                url=source.url,
                text=source.text,
                sourceRef=source.source_ref,
                position=source.position,
                status=source.status.value,
                assessmentReason=source.assessment_reason,
                assessmentConfidence=source.assessment_confidence,
            )
            for source in sorted(recipe.sources, key=lambda item: item.position if item.position is not None else 9999)
        ],
        reviewFlags=[_serialize_flag(flag) for flag in recipe.review_flags],
    )


def list_recipes(session: Session) -> RecipeListOut:
    recipes = session.scalars(select(Recipe).order_by(Recipe.created_at.desc())).all()
    return RecipeListOut(
        items=[RecipeListItemOut(id=recipe.id, title=recipe.title, note=recipe.note, updatedAt=recipe.updated_at) for recipe in recipes]
    )


def get_recipe_detail(session: Session, recipe_id: str) -> RecipeDetailOut:
    recipe = session.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.images),
            selectinload(Recipe.sources),
            selectinload(Recipe.review_flags),
        )
    )
    if recipe is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Recipe not found.", status_code=404)
    return _serialize_recipe_detail(recipe)


def patch_recipe(session: Session, recipe_id: str, patch: RecipePatchIn) -> RecipeDetailOut:
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Recipe not found.", status_code=404)
    if patch.title is not None:
        recipe.title = patch.title.strip()
    if patch.servings is not None:
        recipe.servings = patch.servings
    if patch.cookTimeMinutes is not None:
        recipe.cook_time_minutes = patch.cookTimeMinutes
    if patch.instructions is not None:
        recipe.instructions = [step.strip() for step in patch.instructions if step.strip()]
    if patch.note is not None:
        recipe.note = patch.note.strip()[: get_settings().max_recipe_note_chars]
    session.commit()
    return get_recipe_detail(session, recipe_id)


def set_review_flag_status(session: Session, recipe_id: str, flag_id: str, status: str) -> ReviewFlagOut:
    flag = session.scalar(select(RecipeReviewFlag).where(RecipeReviewFlag.id == flag_id, RecipeReviewFlag.recipe_id == recipe_id))
    if flag is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Review flag not found.", status_code=404)
    if status == "resolved":
        flag.status = RecipeReviewFlagStatus.RESOLVED
        flag.resolved_at = datetime.now(timezone.utc)
    else:
        flag.status = RecipeReviewFlagStatus.OPEN
        flag.resolved_at = None
    session.commit()
    session.refresh(flag)
    return _serialize_flag(flag)
