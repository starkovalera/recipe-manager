from datetime import datetime, timezone
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError, ErrorCode
from app.core.logging import log_info
from app.models import (
    Ingredient,
    Recipe,
    RecipeImage,
    RecipeResource,
    RecipeResourceStatus,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    SourceType,
    Tag,
)
from app.schemas.recipes import (
    CoverOptionOut,
    IngredientOut,
    RecipeCollectionOut,
    RecipeDetailOut,
    RecipeImageOut,
    RecipeListItemOut,
    RecipeListOut,
    RecipePatchIn,
    RecipeResourceOut,
    ReviewFlagOut,
)
from app.services.recipe_limits import validate_recipe_note, validate_recipe_size

logger = logging.getLogger(__name__)


def _image_url(storage_key: str) -> str:
    return f"/media/{storage_key}"


def _serialize_image(image) -> RecipeImageOut:
    return RecipeImageOut(
        id=image.id,
        mediaUrl=_image_url(image.storage_key),
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


def _serialize_resource(resource: RecipeResource) -> RecipeResourceOut:
    return RecipeResourceOut(
        id=resource.id,
        type=resource.type.value,
        source=resource.source.value,
        role=resource.role.value,
        parentResourceId=resource.parent_resource_id,
        url=resource.url,
        imageId=resource.image_id,
        text=resource.text,
        position=resource.position,
        status=resource.status.value,
        assessmentReason=resource.assessment_reason,
        assessmentConfidence=resource.assessment_confidence,
    )


def _resource_sort_key(resource: RecipeResource) -> tuple[int, str]:
    return (resource.position if resource.position is not None else 9999, resource.id)


def _visible_image_resources(recipe: Recipe) -> list[RecipeResource]:
    resources = [
        resource
        for resource in recipe.resources
        if resource.type == SourceType.IMAGE
        and resource.image is not None
        and (resource.status != RecipeResourceStatus.DELETED or resource.image_id == recipe.cover_image_id)
    ]
    return sorted(resources, key=_resource_sort_key)


def _cover_options(recipe: Recipe, image_resources: list[RecipeResource], cover_image: RecipeImage | None) -> list[CoverOptionOut]:
    options: list[CoverOptionOut] = [
        CoverOptionOut(
            kind="DEFAULT",
            image=None,
            label="Default image",
            selected=recipe.cover_image_id is None,
        )
    ]
    label_index = 1
    for resource in image_resources:
        if resource.image is None:
            continue
        is_selected = cover_image is not None and resource.image_id == cover_image.id
        if is_selected:
            label = "Current cover"
        else:
            label = f"Image {label_index}"
            label_index += 1
        options.append(
            CoverOptionOut(
                kind="IMAGE",
                image=_serialize_image(resource.image),
                label=label,
                selected=is_selected,
            )
        )
    return options


def _serialize_recipe_detail(recipe: Recipe) -> RecipeDetailOut:
    image_resources = _visible_image_resources(recipe)
    cover_image = next((image for image in recipe.images if image.id == recipe.cover_image_id), None)
    visible_resources = [resource for resource in recipe.resources if resource.status != RecipeResourceStatus.DELETED]
    debug_resources = list(recipe.resources)
    return RecipeDetailOut(
        id=recipe.id,
        title=recipe.title,
        coverImage=_serialize_image(cover_image) if cover_image else None,
        note=recipe.note,
        updatedAt=recipe.updated_at,
        hasOpenReviewFlags=any(flag.status == RecipeReviewFlagStatus.OPEN for flag in recipe.review_flags),
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
        images=[_serialize_image(resource.image) for resource in image_resources if resource.image is not None],
        coverOptions=_cover_options(recipe, image_resources, cover_image),
        collections=[
            RecipeCollectionOut(id=collection.id, name=collection.name)
            for collection in sorted(recipe.collections, key=lambda item: item.name)
        ],
        resources=[_serialize_resource(resource) for resource in sorted(visible_resources, key=_resource_sort_key)],
        sources=[_serialize_resource(resource) for resource in sorted(visible_resources, key=_resource_sort_key)],
        debugResources=[_serialize_resource(resource) for resource in sorted(debug_resources, key=_resource_sort_key)],
        debugSources=[_serialize_resource(resource) for resource in sorted(debug_resources, key=_resource_sort_key)],
        reviewFlags=[_serialize_flag(flag) for flag in recipe.review_flags],
    )


def list_recipes(session: Session, owner_id: str) -> RecipeListOut:
    recipes = session.scalars(
        select(Recipe)
        .where(Recipe.owner_id == owner_id)
        .options(selectinload(Recipe.images), selectinload(Recipe.review_flags))
        .order_by(Recipe.created_at.desc())
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
                hasOpenReviewFlags=any(flag.status == RecipeReviewFlagStatus.OPEN for flag in recipe.review_flags),
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
            selectinload(Recipe.resources).selectinload(RecipeResource.image),
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
    if patch.ingredients is not None or patch.instructions is not None:
        validate_recipe_size(
            patch.ingredients if patch.ingredients is not None else recipe.ingredients,
            patch.instructions if patch.instructions is not None else recipe.instructions,
        )
    if patch.note is not None:
        validate_recipe_note(patch.note)
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
        recipe.note = patch.note.strip()
    if patch.coverSelection is not None:
        if patch.coverSelection.kind == "DEFAULT":
            recipe.cover_image_id = None
        elif patch.coverSelection.imageId:
            image = session.scalar(select(RecipeImage).where(RecipeImage.id == patch.coverSelection.imageId, RecipeImage.recipe_id == recipe.id))
            if image is None:
                raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Cover image not found.", status_code=404)
            recipe.cover_image_id = image.id
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


def _load_recipe_for_resource_mutation(session: Session, recipe_id: str, owner_id: str) -> Recipe:
    recipe = session.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id, Recipe.owner_id == owner_id)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.images),
            selectinload(Recipe.resources).selectinload(RecipeResource.children),
            selectinload(Recipe.review_flags),
            selectinload(Recipe.tags),
            selectinload(Recipe.collections),
        )
    )
    if recipe is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Recipe not found.", status_code=404)
    return recipe


def _is_current_cover_resource(recipe: Recipe, resource: RecipeResource) -> bool:
    return resource.image_id is not None and resource.image_id == recipe.cover_image_id


def patch_recipe_resource_status(session: Session, recipe_id: str, owner_id: str, resource_id: str, status: str) -> RecipeDetailOut:
    recipe = _load_recipe_for_resource_mutation(session, recipe_id, owner_id)
    resource = next((item for item in recipe.resources if item.id == resource_id and item.owner_id == owner_id), None)
    if resource is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Recipe resource not found.", status_code=404)

    if status == "used":
        resource.status = RecipeResourceStatus.USED
    elif status == "deleted":
        if _is_current_cover_resource(recipe, resource):
            raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Current cover resource cannot be deleted.", status_code=409)
        resource.status = RecipeResourceStatus.DELETED
        if resource.type == SourceType.URL:
            for child in resource.children:
                if not _is_current_cover_resource(recipe, child):
                    child.status = RecipeResourceStatus.DELETED
    else:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Unsupported source status.", status_code=400)

    session.commit()
    return get_recipe_detail(session, recipe_id, owner_id)
