from datetime import datetime, timezone
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.core.logging import log_info
from app.models import CoverImageSource, Ingredient, Recipe, RecipeImage, RecipeReviewFlag, RecipeReviewFlagStatus, Tag
from app.schemas.recipes import (
    CoverOptionOut,
    IngredientOut,
    RecipeCollectionOut,
    RecipeDetailOut,
    RecipeImageOut,
    RecipeListItemOut,
    RecipeListOut,
    RecipePatchIn,
    RecipeSourceOut,
    ReviewFlagOut,
)

logger = logging.getLogger(__name__)


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


def _cover_options(recipe: Recipe, source_images: list[RecipeImage], cover_image: RecipeImage | None) -> list[CoverOptionOut]:
    options = [
        CoverOptionOut(
            kind="DEFAULT",
            image=None,
            label="Default image",
            selected=recipe.cover_image_id is None or recipe.cover_image_source == CoverImageSource.DEFAULT,
        )
    ]
    for image in source_images:
        options.append(
            CoverOptionOut(
                kind="IMAGE",
                image=_serialize_image(image),
                label=image.original_name,
                selected=cover_image is not None and cover_image.id == image.id,
            )
        )
    return options


def _serialize_recipe_detail(recipe: Recipe) -> RecipeDetailOut:
    source_images = sorted([image for image in recipe.images if image.role.value == "SOURCE"], key=lambda item: item.position)
    cover_image = next((image for image in recipe.images if image.id == recipe.cover_image_id), None)
    return RecipeDetailOut(
        id=recipe.id,
        title=recipe.title,
        coverImage=_serialize_image(cover_image) if cover_image else None,
        note=recipe.note,
        updatedAt=recipe.updated_at,
        servings=recipe.servings,
        cookTimeMinutes=recipe.cook_time_minutes,
        nutritionEstimate=recipe.nutrition_estimate,
        authorName=recipe.author_name,
        sourceName=recipe.source_name.value,
        tags=sorted(tag.name for tag in recipe.tags),
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
        coverImageSource=recipe.cover_image_source.value if recipe.cover_image_source else None,
        coverOptions=_cover_options(recipe, source_images, cover_image),
        collections=[
            RecipeCollectionOut(id=collection.id, name=collection.name)
            for collection in sorted(recipe.collections, key=lambda item: item.name)
        ],
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


def list_recipes(session: Session, owner_id: str) -> RecipeListOut:
    recipes = session.scalars(
        select(Recipe).where(Recipe.owner_id == owner_id).options(selectinload(Recipe.images)).order_by(Recipe.created_at.desc())
    ).all()
    bind = session.get_bind()
    log_info(
        logger,
        "[recipes.recipes] Listed recipes",
        ownerId=owner_id,
        recipeCount=len(recipes),
        recipeIds=[recipe.id for recipe in recipes],
        databaseUrl=str(bind.url) if bind is not None else None,
    )
    return RecipeListOut(
        items=[
            RecipeListItemOut(
                id=recipe.id,
                title=recipe.title,
                coverImage=_serialize_image(next((image for image in recipe.images if image.id == recipe.cover_image_id), None))
                if recipe.cover_image_id
                else None,
                note=recipe.note,
                updatedAt=recipe.updated_at,
            )
            for recipe in recipes
        ]
    )


def get_recipe_detail(session: Session, recipe_id: str, owner_id: str) -> RecipeDetailOut:
    recipe = session.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id, Recipe.owner_id == owner_id)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.images),
            selectinload(Recipe.sources),
            selectinload(Recipe.review_flags),
            selectinload(Recipe.tags),
            selectinload(Recipe.collections),
        )
    )
    if recipe is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Recipe not found.", status_code=404)
    return _serialize_recipe_detail(recipe)


def patch_recipe(session: Session, recipe_id: str, owner_id: str, patch: RecipePatchIn) -> RecipeDetailOut:
    recipe = session.scalar(select(Recipe).where(Recipe.id == recipe_id, Recipe.owner_id == owner_id))
    if recipe is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Recipe not found.", status_code=404)
    if patch.title is not None:
        recipe.title = patch.title.strip()
    if patch.servings is not None:
        recipe.servings = patch.servings
    if patch.cookTimeMinutes is not None:
        recipe.cook_time_minutes = patch.cookTimeMinutes
    if patch.nutritionEstimate is not None:
        recipe.nutrition_estimate = patch.nutritionEstimate.model_dump()
    if patch.ingredients is not None:
        recipe.ingredients = [
            Ingredient(
                name=ingredient.name.strip(),
                quantity=ingredient.quantity.strip() if ingredient.quantity else None,
                unit=ingredient.unit.strip() if ingredient.unit else None,
                note=ingredient.note.strip() if ingredient.note else None,
                position=index,
            )
            for index, ingredient in enumerate(patch.ingredients)
            if ingredient.name.strip()
        ]
    if patch.instructions is not None:
        recipe.instructions = [step.strip() for step in patch.instructions if step.strip()]
    if patch.tags is not None:
        tags: list[Tag] = []
        for name in sorted({tag.strip() for tag in patch.tags if tag.strip()}):
            tag = session.scalar(select(Tag).where(Tag.owner_id == recipe.owner_id, Tag.name == name))
            if tag is None:
                tag = Tag(owner_id=recipe.owner_id, name=name)
                session.add(tag)
                session.flush()
            tags.append(tag)
        recipe.tags = tags
    if patch.note is not None:
        recipe.note = patch.note.strip()[: get_settings().max_recipe_note_chars]
    if patch.coverSelection is not None:
        if patch.coverSelection.kind == "DEFAULT":
            recipe.cover_image_id = None
            recipe.cover_image_source = CoverImageSource.DEFAULT
        elif patch.coverSelection.imageId:
            image = session.scalar(select(RecipeImage).where(RecipeImage.id == patch.coverSelection.imageId, RecipeImage.recipe_id == recipe.id))
            if image is None:
                raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Cover image not found.", status_code=404)
            recipe.cover_image_id = image.id
            recipe.cover_image_source = CoverImageSource.USER
    session.commit()
    return get_recipe_detail(session, recipe_id, owner_id)


def delete_recipe(session: Session, recipe_id: str, owner_id: str) -> None:
    recipe = session.scalar(select(Recipe).where(Recipe.id == recipe_id, Recipe.owner_id == owner_id))
    if recipe is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Recipe not found.", status_code=404)
    session.delete(recipe)
    session.commit()


def set_review_flag_status(session: Session, recipe_id: str, owner_id: str, flag_id: str, status: str) -> ReviewFlagOut:
    flag = session.scalar(
        select(RecipeReviewFlag).where(
            RecipeReviewFlag.id == flag_id,
            RecipeReviewFlag.recipe_id == recipe_id,
            RecipeReviewFlag.owner_id == owner_id,
        )
    )
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
