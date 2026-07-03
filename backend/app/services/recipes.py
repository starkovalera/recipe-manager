from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.embeddings.service import enqueue_recipe_embedding, prepare_recipe_embedding
from app.models import (
    Ingredient,
    Recipe,
    RecipeResource,
    RecipeResourceStatus,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    SourceName,
    SourceType,
)
from app.recipes.filters import RecipeListFilters
from app.recipes.queries import (
    count_recipes,
    get_recipe as query_recipe,
    get_recipe_detail as query_recipe_detail,
    get_recipe_for_resource_mutation as query_recipe_for_resource_mutation,
    get_recipe_image,
    get_recipe_review_flag,
    list_recipes as query_recipes,
)
from app.schemas.recipes import RecipePatchIn
from app.services.recipe_limits import validate_recipe_note, validate_recipe_size
from app.services.search_text import build_ingredient_search_name, refresh_recipe_search_text
from app.tags.queries import list_active_tags_by_ids


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _apply_ingredient_fields(ingredient: Ingredient, name: str, quantity: str | None, unit: str | None, note: str | None, position: int) -> None:
    cleaned_name = name.strip()
    ingredient.name = cleaned_name
    ingredient.search_name = build_ingredient_search_name(cleaned_name)
    ingredient.quantity = _clean_optional(quantity)
    ingredient.unit = _clean_optional(unit)
    ingredient.note = _clean_optional(note)
    ingredient.position = position


def list_recipes(session: Session, owner_id: str, *, filters: RecipeListFilters, limit: int, offset: int) -> tuple[list[Recipe], int]:
    recipes = query_recipes(session, owner_id, filters=filters, limit=limit, offset=offset)
    total = count_recipes(session, owner_id, filters=filters)
    return recipes, total


def get_recipe_detail(session: Session, recipe_id: str, owner_id: str) -> Recipe:
    recipe = query_recipe_detail(session, recipe_id, owner_id)
    if recipe is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Recipe not found.", status_code=404)
    return recipe


def _validate_recipe_patch(recipe: Recipe, patch: RecipePatchIn) -> None:
    if patch.ingredients is not None or patch.instructions is not None:
        validate_recipe_size(
            patch.ingredients if patch.ingredients is not None else recipe.ingredients,
            patch.instructions if patch.instructions is not None else recipe.instructions,
        )
    if patch.note is not None:
        validate_recipe_note(patch.note)


def _apply_recipe_scalar_patch(recipe: Recipe, patch: RecipePatchIn) -> None:
    if patch.title is not None:
        recipe.title = patch.title.strip()
    if patch.source_name is not None:
        recipe.source_name = SourceName(patch.source_name)
    if "author_name" in patch.model_fields_set:
        recipe.author_name = _clean_optional(patch.author_name)
    if patch.servings is not None:
        recipe.servings = patch.servings
    if patch.cook_time_minutes is not None:
        recipe.cook_time_minutes = patch.cook_time_minutes
    if patch.nutrition_estimate is not None:
        recipe.nutrition_estimate = patch.nutrition_estimate.model_dump(by_alias=True)
    if patch.instructions is not None:
        recipe.instructions = [step.strip() for step in patch.instructions if step.strip()]
    if patch.note is not None:
        recipe.note = patch.note.strip()


def _replace_recipe_ingredients(recipe: Recipe, patch: RecipePatchIn) -> None:
    if patch.ingredients is None:
        return

    existing_by_id = {ingredient.id: ingredient for ingredient in recipe.ingredients}
    next_ingredients: list[Ingredient] = []
    seen_ids: set[str] = set()
    for index, ingredient_in in enumerate(patch.ingredients):
        if not ingredient_in.name.strip():
            raise ApiError(ErrorCode.INVALID_INGREDIENT, "Ingredient name is required.")
        if ingredient_in.id is not None:
            ingredient = existing_by_id.get(ingredient_in.id)
            if ingredient is None or ingredient.id in seen_ids:
                raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Ingredient not found.", status_code=404)
            seen_ids.add(ingredient.id)
        else:
            ingredient = Ingredient()
        _apply_ingredient_fields(
            ingredient,
            ingredient_in.name,
            ingredient_in.quantity,
            ingredient_in.unit,
            ingredient_in.note,
            index,
        )
        next_ingredients.append(ingredient)
    recipe.ingredients = next_ingredients


def _apply_recipe_tags(session: Session, recipe: Recipe, patch: RecipePatchIn) -> None:
    if patch.tag_ids is None:
        return

    unique_tag_ids = list(dict.fromkeys(patch.tag_ids))
    tags = list_active_tags_by_ids(session, recipe.owner_id, unique_tag_ids)
    if len(tags) != len(unique_tag_ids):
        raise ApiError(ErrorCode.INVALID_TAG, "Some tags are invalid.")
    by_id = {tag.id: tag for tag in tags}
    recipe.tags = [by_id[tag_id] for tag_id in unique_tag_ids]


def _apply_cover_selection(session: Session, recipe: Recipe, patch: RecipePatchIn) -> None:
    if patch.cover_selection is None:
        return

    if patch.cover_selection.kind == "DEFAULT":
        recipe.cover_image_id = None
        return
    if patch.cover_selection.image_id:
        image = get_recipe_image(session, patch.cover_selection.image_id, recipe.id)
        if image is None:
            raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Cover image not found.", status_code=404)
        recipe.cover_image_id = image.id


def patch_recipe(session: Session, recipe_id: str, owner_id: str, patch: RecipePatchIn) -> Recipe:
    recipe = query_recipe(session, recipe_id, owner_id)
    if recipe is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Recipe not found.", status_code=404)

    _validate_recipe_patch(recipe, patch)
    _apply_recipe_scalar_patch(recipe, patch)
    _replace_recipe_ingredients(recipe, patch)
    _apply_recipe_tags(session, recipe, patch)
    _apply_cover_selection(session, recipe, patch)

    refresh_recipe_search_text(recipe)
    _, should_enqueue_embedding = prepare_recipe_embedding(recipe)
    session.commit()
    if should_enqueue_embedding:
        enqueue_recipe_embedding(recipe.id)
    return get_recipe_detail(session, recipe_id, owner_id)


def delete_recipe(session: Session, recipe_id: str, owner_id: str) -> None:
    recipe = query_recipe(session, recipe_id, owner_id)
    if recipe is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Recipe not found.", status_code=404)
    session.delete(recipe)
    session.commit()


def set_review_flag_status(session: Session, recipe_id: str, owner_id: str, flag_id: str, status: str) -> RecipeReviewFlag:
    flag = get_recipe_review_flag(session, flag_id, recipe_id, owner_id)
    if flag is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Review flag not found.", status_code=404)
    if status == "resolved":
        flag.status = RecipeReviewFlagStatus.RESOLVED
        flag.resolved_at = datetime.now(timezone.utc)
    else:
        flag.status = RecipeReviewFlagStatus.OPEN
        flag.resolved_at = None
    _, should_enqueue_embedding = prepare_recipe_embedding(flag.recipe)
    session.commit()
    if should_enqueue_embedding:
        enqueue_recipe_embedding(recipe_id)
    session.refresh(flag)
    return flag


def _load_recipe_for_resource_mutation(session: Session, recipe_id: str, owner_id: str) -> Recipe:
    recipe = query_recipe_for_resource_mutation(session, recipe_id, owner_id)
    if recipe is None:
        raise ApiError(ErrorCode.RECIPE_NOT_FOUND, "Recipe not found.", status_code=404)
    return recipe


def _is_current_cover_resource(recipe: Recipe, resource: RecipeResource) -> bool:
    return resource.image_id is not None and resource.image_id == recipe.cover_image_id


def patch_recipe_resource_status(session: Session, recipe_id: str, owner_id: str, resource_id: str, status: str) -> Recipe:
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
